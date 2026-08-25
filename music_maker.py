"""
music_maker.py
===============
يجلب مقطع موسيقى خلفية مجاني يناسب مزاج الكتاب، من مكتبة Jamendo
(مجانية بالكامل). لو ما فيه مفتاح، يُكمل الفيديو بدون موسيقى تلقائياً.
"""

import os
import random
import requests

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
MUSIC_DIR = os.path.join(TEMP_DIR, "music")
os.makedirs(MUSIC_DIR, exist_ok=True)

JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID", "")

JAMENDO_SEARCH_URL = "https://api.jamendo.com/v3.0/tracks/"

MOOD_MUSIC_TAGS = {
    "hopeful": ["uplifting", "inspiring", "hopeful", "warm"],
    "dark": ["dark", "dramatic", "tense"],
    "mysterious": ["mysterious", "ambient", "suspense"],
    "sad": ["sad", "melancholic", "emotional", "piano"],
    "motivational": ["epic", "motivational", "inspiring", "energetic"],
    "neutral": ["ambient", "calm", "cinematic"],
}


def fetch_background_music(output_path: str, mood: str = "neutral", max_retries: int = 3) -> str:
    if not JAMENDO_CLIENT_ID:
        print("[music_maker] لا يوجد مفتاح Jamendo - سيُنشأ الفيديو بدون موسيقى.")
        return None

    tags = MOOD_MUSIC_TAGS.get(mood, MOOD_MUSIC_TAGS["neutral"])

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            tag = random.choice(tags)
            print(f"[music_maker] بحث عن موسيقى بمزاج '{mood}' (كلمة: '{tag}', محاولة {attempt})")

            params = {
                "client_id": JAMENDO_CLIENT_ID,
                "format": "json",
                "limit": 10,
                "fuzzytags": tag,
                "audioformat": "mp32",
                "order": "popularity_total",
            }
            response = requests.get(JAMENDO_SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                raise RuntimeError("لا توجد نتائج مطابقة.")

            chosen = random.choice(results)
            audio_url = chosen.get("audio")

            if not audio_url:
                raise RuntimeError("لا يوجد رابط تنزيل صالح.")

            audio_response = requests.get(audio_url, timeout=60)
            audio_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(audio_response.content)

            print(f"[music_maker] تم تحميل: {chosen.get('name', 'unknown')}")
            return output_path

        except Exception as e:
            last_error = e
            print(f"[music_maker] فشلت المحاولة {attempt}: {e}")

    print(f"[music_maker] تعذّر جلب موسيقى خلفية: {last_error}. سيتم إنشاء الفيديو بدون موسيقى.")
    return None


if __name__ == "__main__":
    output_path = os.path.join(MUSIC_DIR, "background.mp3")
    result = fetch_background_music(output_path, mood="motivational")
    print("النتيجة:", result)
