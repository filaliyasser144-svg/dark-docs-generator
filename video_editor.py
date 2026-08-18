"""
video_editor.py
================
يقوم بمونتاج الفيديو النهائي: يدمج كل صورة مع مقطعها الصوتي المقابل،
مع تطبيق تأثير Ken Burns (تكبير/تحريك بطيء) لإضفاء طابع سينمائي،
ثم يدمج كل المشاهد في فيديو واحد متكامل.

المخرجات:
    - ملف فيديو نهائي: output/final_video.mp4
"""

import os
import json
import random

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx,
)

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

KEN_BURNS_MAX_ZOOM = 1.15
CROSSFADE_DURATION = 1.0


def apply_ken_burns_effect(image_clip: ImageClip, duration: float) -> ImageClip:
    clip = image_clip.resize(height=int(VIDEO_HEIGHT * KEN_BURNS_MAX_ZOOM * 1.2))

    zoom_in = random.choice([True, False])

    if zoom_in:
        start_scale, end_scale = 1.0, KEN_BURNS_MAX_ZOOM
    else:
        start_scale, end_scale = KEN_BURNS_MAX_ZOOM, 1.0

    def resize_func(t):
        progress = t / duration if duration > 0 else 0
        scale = start_scale + (end_scale - start_scale) * progress
        return scale

    animated_clip = clip.resize(resize_func)
    animated_clip = animated_clip.set_position(("center", "center"))

    return animated_clip


def build_scene_clip(image_path: str, audio_path: str) -> CompositeVideoClip:
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    base_image_clip = ImageClip(image_path).set_duration(duration)
    animated_clip = apply_ken_burns_effect(base_image_clip, duration)

    scene = CompositeVideoClip(
        [animated_clip.set_position("center")], size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_duration(duration)

    scene = scene.set_audio(audio_clip)

    scene = scene.fx(vfx.fadein, CROSSFADE_DURATION).fx(vfx.fadeout, CROSSFADE_DURATION)

    return scene


def create_final_video(scenes: list, image_paths: list, audio_paths: list) -> str:
    if len(image_paths) != len(audio_paths):
        raise ValueError("عدد الصور لا يساوي عدد ملفات الصوت.")

    print(f"[video_editor] بناء {len(image_paths)} مشهداً...")

    scene_clips = []
    for idx, (img_path, audio_path) in enumerate(zip(image_paths, audio_paths), start=1):
        print(f"[video_editor] معالجة المشهد {idx}/{len(image_paths)}...")
        clip = build_scene_clip(img_path, audio_path)
        scene_clips.append(clip)

    print("[video_editor] دمج كل المشاهد في فيديو نهائي...")
    final_video = concatenate_videoclips(scene_clips, method="compose")

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

    images_dir = os.path.join(TEMP_DIR, "images")
    audio_dir = os.path.join(TEMP_DIR, "audio")

    image_files = sorted(
        [os.path.join(images_dir, f) for f in os.listdir(images_dir)]
    )
    audio_files = sorted(
        [os.path.join(audio_dir, f) for f in os.listdir(audio_dir)]
    )

    create_final_video(scenes_data, image_files, audio_files)
