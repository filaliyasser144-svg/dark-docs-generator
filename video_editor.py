"""
video_editor.py
================
يبني فيديو تلخيص الكتاب: خلفية ثابتة + غلاف نابض + مؤشر صوت متحرك
(Equalizer) + موسيقى.
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw

from moviepy.editor import (
    ImageClip,
    VideoClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_audioclips,
    afx,
)

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FPS = 15

COVER_BASE_WIDTH = 260
COVER_PULSE_STRENGTH = 0.10
COVER_RIGHT_MARGIN = 60

MUSIC_VOLUME_RATIO = 0.12


def prepare_static_background(background_path: str) -> np.ndarray:
    img = Image.open(background_path).convert("RGB")

    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        new_height = VIDEO_HEIGHT
        new_width = int(img_ratio * new_height)
    else:
        new_width = VIDEO_WIDTH
        new_height = int(new_width / img_ratio)

    img = img.resize((new_width, new_height))

    left = (new_width - VIDEO_WIDTH) // 2
    top = (new_height - VIDEO_HEIGHT) // 2
    img = img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))

    frame = np.array(img).astype("float32")

    frame[:, :, 0] *= 0.95
    frame[:, :, 2] *= 1.03
    frame *= 0.90

    h, w = frame.shape[0], frame.shape[1]
    y, x = np.ogrid[:h, :w]
    center_x, center_y = w / 2, h / 2
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    vignette = 1 - 0.35 * (dist / max_dist) ** 2
    vignette = np.clip(vignette, 0.55, 1.0)
    frame *= vignette[:, :, np.newaxis]

    return np.clip(frame, 0, 255).astype("uint8")


def compute_audio_envelope(audio_clip: AudioFileClip, sample_rate: int = 15) -> np.ndarray:
    try:
        raw = audio_clip.to_soundarray(fps=sample_rate)
        if raw.ndim > 1:
            raw = raw.mean(axis=1)
        envelope = np.abs(raw)

        window = 3
        kernel = np.ones(window) / window
        envelope = np.convolve(envelope, kernel, mode="same")

        max_val = envelope.max() if envelope.max() > 0 else 1
        envelope = envelope / max_val

        return envelope
    except Exception as e:
        print(f"[video_editor] تعذّر حساب نبض الصوت: {e}. سيُستخدم نبض ثابت خفيف.")
        return np.array([0.5])


def make_pulsing_cover(cover_path: str, envelope: np.ndarray, duration: float, sample_rate: int = 15):
    base_cover = ImageClip(cover_path).resize(width=COVER_BASE_WIDTH).set_duration(duration)

    def scale_func(t):
        idx = min(int(t * sample_rate), len(envelope) - 1)
        return 1.0 + COVER_PULSE_STRENGTH * envelope[idx]

    pulsing_cover = base_cover.resize(scale_func)

    def position_func(t):
        current_width = COVER_BASE_WIDTH * scale_func(t)
        x = VIDEO_WIDTH - COVER_RIGHT_MARGIN - current_width
        return (x, "center")

    pulsing_cover = pulsing_cover.set_position(position_func)
    return pulsing_cover


EQUALIZER_WIDTH = 220
EQUALIZER_HEIGHT = 70
EQUALIZER_BARS = 6


def make_equalizer_clip(envelope: np.ndarray, duration: float, sample_rate: int = 15):
    def make_frame(t):
        idx = min(int(t * sample_rate), len(envelope) - 1)
        level = envelope[idx]

        img = Image.new("RGB", (EQUALIZER_WIDTH, EQUALIZER_HEIGHT), (15, 15, 20))
        draw = ImageDraw.Draw(img)

        gap = 8
        bar_width = (EQUALIZER_WIDTH - gap * (EQUALIZER_BARS + 1)) / EQUALIZER_BARS

        for i in range(EQUALIZER_BARS):
            phase_offset = i * 0.9
            variation = 0.5 + 0.5 * abs(np.sin(t * 5 + phase_offset))
            bar_level = max(0.08, level * variation)
            bar_height = int(EQUALIZER_HEIGHT * bar_level)

            x0 = gap + i * (bar_width + gap)
            y1 = EQUALIZER_HEIGHT - 4
            y0 = y1 - bar_height
            x1 = x0 + bar_width

            draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))

        return np.array(img)

    return VideoClip(make_frame, duration=duration)


def add_background_music(narration_audio: AudioFileClip, music_path: str) -> AudioFileClip:
    if not music_path or not os.path.exists(music_path):
        print("[video_editor] لا توجد موسيقى خلفية - سيُنشأ الفيديو بدونها.")
        return narration_audio

    try:
        music = AudioFileClip(music_path)
        target_duration = narration_audio.duration

        if music.duration < target_duration:
            music = music.fx(afx.audio_loop, duration=target_duration)
        else:
            music = music.subclip(0, target_duration)

        music = music.fx(afx.volumex, MUSIC_VOLUME_RATIO)
        music = music.audio_fadein(2).audio_fadeout(3)

        combined = CompositeAudioClip([narration_audio, music])
        print("[video_editor] تمت إضافة الموسيقى الخلفية بنجاح.")
        return combined

    except Exception as e:
        print(f"[video_editor] تعذّر دمج الموسيقى الخلفية: {e}. سيُكمل الفيديو بدونها.")
        return narration_audio


def create_final_video(
    audio_paths: list,
    background_path: str,
    cover_path: str,
    music_path: str = None,
) -> str:
    print("[video_editor] دمج مقاطع الصوت (الراوي)...")
    narration_clips = [AudioFileClip(p) for p in audio_paths]
    narration_audio = concatenate_audioclips(narration_clips)
    total_duration = narration_audio.duration
    print(f"[video_editor] مدة الفيديو الإجمالية: {total_duration / 60:.1f} دقيقة")

    print("[video_editor] تجهيز الخلفية الثابتة...")
    background_frame = prepare_static_background(background_path)
    background_clip = ImageClip(background_frame).set_duration(total_duration)

    print("[video_editor] حساب نبض غلاف الكتاب حسب الصوت...")
    envelope = compute_audio_envelope(narration_audio, sample_rate=FPS)
    cover_clip = make_pulsing_cover(cover_path, envelope, total_duration, sample_rate=FPS)

    print("[video_editor] إضافة مؤشر الصوت المتحرك (Equalizer)...")
    equalizer_clip = make_equalizer_clip(envelope, total_duration, sample_rate=FPS)
    equalizer_x = VIDEO_WIDTH - COVER_RIGHT_MARGIN - COVER_BASE_WIDTH
    equalizer_y = VIDEO_HEIGHT - EQUALIZER_HEIGHT - 30
    equalizer_clip = equalizer_clip.set_position((equalizer_x, equalizer_y))

    print("[video_editor] دمج الخلفية مع الغلاف ومؤشر الصوت...")
    final_visual = CompositeVideoClip(
        [background_clip, cover_clip, equalizer_clip], size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_duration(total_duration)

    print("[video_editor] دمج الموسيقى الخلفية مع الراوي...")
    final_audio = add_background_music(narration_audio, music_path)
    final_video = final_visual.set_audio(final_audio)

    print("[video_editor] تصدير الفيديو النهائي (قد يستغرق وقتاً حسب الطول)...")
    final_video.write_videofile(
        FINAL_VIDEO_PATH,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="veryfast",
    )

    final_video.close()
    for clip in narration_clips:
        clip.close()

    print(f"[video_editor] تم إنشاء الفيديو النهائي: {FINAL_VIDEO_PATH}")
    return FINAL_VIDEO_PATH


if __name__ == "__main__":
    script_path = os.path.join(TEMP_DIR, "script.json")
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    audio_dir = os.path.join(TEMP_DIR, "audio")
    audio_files = sorted([os.path.join(audio_dir, f) for f in os.listdir(audio_dir)])

    assets_dir = os.path.join(TEMP_DIR, "assets")
    background_file = os.path.join(assets_dir, "background.jpg")
    cover_file = os.path.join(assets_dir, "cover.jpg")
    music_file = os.path.join(TEMP_DIR, "music", "background.mp3")

    create_final_video(
        audio_files,
        background_file,
        cover_file,
        music_path=music_file if os.path.exists(music_file) else None,
        )
