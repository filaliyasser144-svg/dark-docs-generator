"""
visuals_maker.py
=================
يجلب مقاطع فيديو حقيقية من Pexels حسب وصف كل مشهد.
"""

import os
import json
import time
import random
import requests

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
CLIPS_DIR = os.path.join(TEMP_DIR, "clips")
os.makedirs(CLIPS_DIR, exist_ok=True)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "ضع_مفتاح_Pexels_هنا")

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

FALLBACK_QUERIES = [
    "dark city street night",
    "crime investigation room",
    "mystery fog night",
    "police lights night",
    "abandoned building dark",
]


def _extract_search_keywords(image_prompt: str) -> str:
    first_part = image_prompt.split(",")[0].strip()
    words = first_part.split()
    return " ".join(words[:6])


def _search_pexels_video(query: str) -> str:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "landscape",
        "size": "medium",
        "per_page": 5,
    }

    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    videos = data.get("videos", [])
    if not videos:
        return None

    chosen = random.choice(videos)

    video_files = sorted(
        chosen.get("video_files", []),
        key=lambda f: f.get("width", 0),
        reverse=True,
    )
    best_file = None
    for f in video_files:
        if f.get("width", 0) <= 1920:
            best_file = f
            break
    if best_file is None and video_files:
        best_file = video_files[-1]

    return best_file["link"] if best_file else None


def download_clip_for_scene(image_prompt: str, output_path: str, max_retries: int = 3) -> str:
    query = _extract_search_keywords(image_prompt)
    candidates = [query] + FALLBACK_QUERIES

    last_error = None
    for attempt, search_query in enumerate(candidates[:max_retries + 1], start=1):
        try:
            print(f"[visuals_maker] بحث عن مقطع فيديو: '{search_query}' (محاولة {attempt})")
            video_url = _search_pexels_video(search_query)

            if not video_url:
                raise RuntimeError("لا توجد نتائج مطابقة.")

            video_response = requests.get(video_url, timeout=120, stream=True)
            video_response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

            return output_path

        except Exception as e:
            last_error = e
            print(f"[visuals_maker] فشلت المحاولة {attempt}: {e}")
            time.sleep(2)

    raise RuntimeError(f"فشل تحميل مقطع الفيديو بعد عدة محاولات: {last_error}")


def generate_all_visuals(scenes: list) -> list:
    clip_paths = []

    for idx, scene in enumerate(scenes, start=1):
        prompt = scene["image_prompt"]
        output_path = os.path.join(CLIPS_DIR, f"scene_{idx:02d}.mp4")

        download_clip_for_scene(prompt, output_path)
        clip_paths.append(output_path)
        print(f"[visuals_maker] تم تحميل: {output_path}")

        time.sleep(1)

    return clip_paths


if __name__ == "__main__":
    script_path = os.path.join(TEMP_DIR, "script.json")
    if not os.path.exists(script_path):
        raise FileNotFoundError(
            "لم يتم العثور على temp/script.json. شغّل script_maker.py أولاً."
        )

    with open(script_path, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    paths = generate_all_visuals(scenes_data)
    print("تم تحميل المقاطع التالية:")
    for p in paths:
        print(" -", p)
