"""
visuals_maker.py
=================
يولّد صوراً سينمائية مظلمة لكل مشهد باستخدام Pollinations.ai،
وهي خدمة توليد صور بالذكاء الاصطناعي **مجانية بالكامل، بدون مفتاح API
وبدون تسجيل حساب** — تكفي طلب GET بسيط لرابط يحتوي على الوصف النصي.

المخرجات:
    - صورة واحدة لكل مشهد داخل temp/images/scene_XX.png
    - قائمة بمسارات هذه الصور (بنفس ترتيب المشاهد)
"""

import os
import json
import time
import random
import urllib.parse
import requests

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
IMAGES_DIR = os.path.join(TEMP_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# =========================================================================
#  Pollinations.ai — خدمة توليد صور مجانية بالكامل، بدون مفتاح API
# =========================================================================
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt/"

POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux")

IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080

STYLE_SUFFIX = (
    ", cinematic lighting, dark moody atmosphere, film noir style, "
    "high contrast shadows, mysterious crime investigation aesthetic, "
    "photorealistic, ultra detailed, 4k"
)


def _build_pollinations_url(prompt: str, seed: int) -> str:
    full_prompt = prompt.strip()
    if "cinematic" not in full_prompt.lower():
        full_prompt += STYLE_SUFFIX

    encoded_prompt = urllib.parse.quote(full_prompt)

    url = (
        f"{POLLINATIONS_BASE_URL}{encoded_prompt}"
        f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
        f"&model={POLLINATIONS_MODEL}"
        f"&seed={seed}"
        f"&nologo=true"
    )
    return url


def generate_image_for_scene(prompt: str, output_path: str, max_retries: int = 4) -> str:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[visuals_maker] توليد صورة... (محاولة {attempt})")

            seed = random.randint(1, 999_999)
            url = _build_pollinations_url(prompt, seed)

            response = requests.get(url, timeout=120)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise RuntimeError(f"الرد ليس صورة صالحة (Content-Type: {content_type})")

            with open(output_path, "wb") as f:
                f.write(response.content)

            return output_path

        except Exception as e:
            last_error = e
            print(f"[visuals_maker] فشلت المحاولة {attempt}: {e}")
            time.sleep(3)

    raise RuntimeError(f"فشل توليد الصورة بعد {max_retries} محاولات: {last_error}")


def generate_all_visuals(scenes: list) -> list:
    image_paths = []

    for idx, scene in enumerate(scenes, start=1):
        prompt = scene["image_prompt"]
        output_path = os.path.join(IMAGES_DIR, f"scene_{idx:02d}.png")

        generate_image_for_scene(prompt, output_path)
        image_paths.append(output_path)
        print(f"[visuals_maker] تم إنشاء: {output_path}")

        time.sleep(1)

    return image_paths


if __name__ == "__main__":
    script_path = os.path.join(TEMP_DIR, "script.json")
    if not os.path.exists(script_path):
        raise FileNotFoundError(
            "لم يتم العثور على temp/script.json. شغّل script_maker.py أولاً."
        )

    with open(script_path, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    paths = generate_all_visuals(scenes_data)
    print("تم إنشاء الصور التالية:")
    for p in paths:
        print(" -", p)
