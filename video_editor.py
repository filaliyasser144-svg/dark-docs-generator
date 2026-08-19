"""
video_editor.py
================
يقوم بمونتاج الفيديو النهائي من مقاطع فيديو حقيقية (بدل الصور الثابتة):
    - يقصّ/يكرّر كل مقطع ليطابق مدة صوت الراوي لنفس المشهد
    - يطبّق مؤثرات سينمائية: تكبير بطيء، تصحيح ألوان مظلم، تظليل حواف،
      وانتقالات تلاشي ناعمة بين المشاهد
    - يدمج التعليق الصوتي لكل مشهد
    - يضيف موسيقى خلفية بصوت منخفض تحت الراوي (إن وُجدت)
"""

import os
import json
import random
import numpy as np

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx,
    afx,
)

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

MAX_ZOOM = 1.12
CROSSFADE_DURATION = 1.0
MUSIC_VOLUME_RATIO = 0.12


def apply_slow_zoom(clip: VideoFileClip, duration: float) -> VideoFileClip:
    def resize_func(t):
        progress = t / duration if duration > 0 else 0
        return 1.0 + (MAX_ZOOM - 1.0) * progress

    return clip.resize(resize_func)


def apply_dark_grading(clip: VideoFileClip) -> VideoFileClip:
    def grade_frame(frame):
        graded = frame.astype("float32")
        graded[:, :, 0] *= 0.92
        graded[:, :, 2] *= 1.05
        graded = graded * 0.88
        return np.clip(graded, 0, 255).astype("uint8")

    return clip.fl_image(grade_frame)


def build_vignette_mask(width: int, height: int) -> np.ndarray:
    y, x = np.ogrid[:height, :width]
    center_x, center_y = width / 2, height / 2
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    mask = 1 - 0.45 * (dist / max_dist) ** 2
    return np.clip(mask, 0.4, 1.0)


_VIGNETTE_CACHE = {}


def apply_vignette(clip: VideoFileClip) -> VideoFileClip:
    key = (clip.w, clip.h)
    if key not in _VIGNETTE_CACHE:
        _VIGNETTE_CACHE[key] = build_vignette_mask(clip.w, clip.h)
    mask = _VIGNETTE_CACHE[key]

    def vignette_frame(frame):
        result = frame.astype("float32") * mask[:, :, np.newaxis]
        return np.clip(result, 0, 255).astype("uint8")

    return clip.fl_image(vignette_frame)


def fit_clip_to_duration(clip: VideoFileClip, target_duration: float) -> VideoFileClip:
    if clip.duration >= target_duration:
        max_start = max(0, clip.duration - target_duration)
        start = random.uniform(0, max_start) if max_start > 0 else 0
        return clip.subclip(start, start + target_duration)
    else:
        loops_needed = int(target_duration // clip.duration) + 1
        looped = concatenate_videoclips([clip] * loops_needed)
        return looped.subclip(0, target_duration)


def resize_and_crop_to_frame(clip: VideoFileClip) -> VideoFileClip:
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        resized = clip.resize(height=VIDEO_HEIGHT)
        resized = resized.crop(x_center=resized.w / 2, width=VIDEO_WIDTH)
    else:
        resized = clip.resize(width=VIDEO_WIDTH)
        resized = resized.crop(y_center=resized.h / 2, height=VIDEO_HEIGHT)

    return resized


def build_scene_clip(video_path: str, audio_path: str) -> CompositeVideoClip:
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    raw_clip = VideoFileClip(video_path).without_audio()
    fitted = fit_clip_to_duration(raw_clip, duration)
    framed = resize_and_crop_to_frame(fitted)

    zoomed = apply_slow_zoom(framed, duration)
    graded = apply_dark_grading(zoomed)
    vignetted = apply_vignette(graded)

    scene = CompositeVideoClip(
        [vignetted.set_position("center")], size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_duration(duration)

    scene = scene.set_audio(audio_clip)
    scene = scene.fx(vfx.fadein, CROSSFADE_DURATION).fx(vfx.fadeout, CROSSFADE_DURATION)

    return scene


def add_background_music(video: CompositeVideoClip, music_path: str) -> CompositeVideoClip:
    if not music_path or not os.path.exists(music_path):
        print("[video_editor] لا توجد موسيقى خلفية - سيُنشأ الفيديو بدونها.")
        return video

    try:
        music = AudioFileClip(music_path)
        target_duration = video.duration

        if music.duration < target_duration:
            music = music.fx(afx.audio_loop, duration=target_duration)
        else:
            music = music.subclip(0, target_duration)

        music = music.fx(afx.volumex, MUSIC_VOLUME_RATIO)
        music = music.audio_fadein(2).audio_fadeout(3)

        combined_audio = CompositeAudioClip([video.audio, music])
        video = video.set_audio(combined_audio)

        print("[video_editor] تمت إضافة الموسيقى الخلفية بنجاح.")
        return video

    except Exception as e:
        print(f"[video_editor] تعذّر دمج الموسيقى الخلفية: {e}. سيُكمل الفيديو بدونها.")
        return video


def create_final_video(
    scenes: list, clip_paths: list, audio_paths: list, music_path: str = None
) -> str:
    if len(clip_paths) != len(audio_paths):
        raise ValueError("عدد مقاطع الفيديو لا يساوي عدد ملفات الصوت.")

    print(f"[video_editor] بناء {len(clip_paths)} مشهداً...")

    scene_clips = []
    for idx, (clip_path, audio_path) in enumerate(zip(clip_paths, audio_paths), start=1):
        print(f"[video_editor] معالجة المشهد {idx}/{len(clip_paths)}...")
        clip = build_scene_clip(clip_path, audio_path)
        scene_clips.append(clip)

    print("[video_editor] دمج كل المشاهد في فيديو نهائي...")
    final_video = concatenate_videoclips(scene_clips, method="compose")

    final_video = add_background_music(final_video, music_path)

    final_video.write_videofile(
        FINAL_VIDEO_PATH,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )

    for clip in scene_clips:
        clip.close()
    final_video.close()

    print(f"[video_editor] تم إنشاء الفيديو النهائي: {FINAL_VIDEO_PATH}")
    return FINAL_VIDEO_PATH


if __name__ == "__main__":
    script_path = os.path.join(TEMP_DIR, "script.json")
    with open(script_path, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    clips_dir = os.path.join(TEMP_DIR, "clips")
    audio_dir = os.path.join(TEMP_DIR, "audio")
    music_file = os.path.join(TEMP_DIR, "music", "background.mp3")

    clip_files = sorted([os.path.join(clips_dir, f) for f in os.listdir(clips_dir)])
    audio_files = sorted([os.path.join(audio_dir, f) for f in os.listdir(audio_dir)])

    create_final_video(
        scenes_data,
        clip_files,
        audio_files,
        music_path=music_file if os.path.exists(music_file) else None,
        )
