"""
book_visuals.py
================
يجلب صورتين لكل فيديو تلخيص كتاب:
    1) غلاف الكتاب — عبر Open Library ثم Google Books (مجاني، بدون مفتاح)
    2) صورة خلفية ثابتة تناسب مزاج الكتاب — عبر Pexels Photos API
"""

import os
import time
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
ASSETS_DIR = os.path.join(TEMP_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "ضع_مفتاح_Pexels_هنا")

MOOD_BACKGROUND_QUERIES = {
    "hopeful": "sunrise field painting warm light landscape",
    "dark": "dark forest fog painting moody landscape",
    "mysterious": "misty forest night painting atmospheric",
    "sad": "rain window painting melancholic landscape",
    "motivational": "mountain summit sunrise painting epic",
    "neutral": "atmospheric landscape painting soft light",
}

MOOD_COLORS = {
    "hopeful": (255, 200, 120),
    "dark": (25, 25, 35),
    "mysterious": (35, 40, 60),
    "sad": (60, 70, 90),
    "motivational": (200, 90, 40),
    "neutral": (70, 70, 80),
}


def fetch_book_cover(title: str, author: str, output_path: str) -> str:
    try:
        query = f"{title} {author}".strip()
        response = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "limit": 3},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        cover_id = None
        for doc in data.get("docs", []):
            if doc.get("cover_i"):
                cover_id = doc["cover_i"]
                break

        if not cover_id:
            print("[book_visuals] لم يُعثر على غلاف عبر Open Library.")
            return None

        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        img_response = requests.get(cover_url, timeout=30)
        img_response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(img_response.content)

        print(f"[book_visuals] تم تحميل غلاف الكتاب (Open Library): {output_path}")
        return output_path

    except Exception as e:
        print(f"[book_visuals] فشل جلب الغلاف من Open Library: {e}")
        return None


def fetch_google_books_cover(title: str, author: str, output_path: str, max_retries: int = 2) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            query = urllib.parse.quote(f"{title} {author}")
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}"

            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                return None

            image_links = items[0].get("volumeInfo", {}).get("imageLinks", {})
            cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")

            if not cover_url:
                return None

            img_response = requests.get(cover_url, timeout=30)
            img_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(img_response.content)

            print(f"[book_visuals] تم تحميل غلاف الكتاب (Google Books): {output_path}")
            return output_path

        except Exception as e:
            print(f"[book_visuals] فشلت محاولة Google Books {attempt}: {e}")
            time.sleep(3)

    return None


def create_placeholder_cover(title: str, mood: str, output_path: str) -> str:
    color = MOOD_COLORS.get(mood, MOOD_COLORS["neutral"])
    img = Image.new("RGB", (400, 600), color=color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28
        )
    except Exception:
        font = ImageFont.load_default()

    words = title.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) > 18:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y = 250
    for line in lines[:5]:
        draw.text((30, y), line, fill=(255, 255, 255), font=font)
        y += 40

    img.save(output_path)
    print(f"[book_visuals] تم إنشاء غلاف بديل: {output_path}")
    return output_path


def fetch_background_image(mood: str, output_path: str) -> str:
    query = MOOD_BACKGROUND_QUERIES.get(mood, MOOD_BACKGROUND_QUERIES["neutral"])

    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "orientation": "landscape", "per_page": 5}

        response = requests.get(
            "https://api.pexels.com/v1/search", headers=headers, params=params, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        photos = data.get("photos", [])
        if not photos:
            raise RuntimeError("لا توجد نتائج مطابقة.")

        photo_url = photos[0]["src"]["large2x"]
        img_response = requests.get(photo_url, timeout=30)
        img_response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(img_response.content)

        print(f"[book_visuals] تم تحميل خلفية بمزاج '{mood}': {output_path}")
        return output_path

    except Exception as e:
        print(f"[book_visuals] فشل جلب صورة الخلفية: {e}")
        return None


def create_placeholder_background(mood: str, output_path: str) -> str:
    color = MOOD_COLORS.get(mood, MOOD_COLORS["neutral"])
    img = Image.new("RGB", (1920, 1080), color=color)
    img.save(output_path)
    print(f"[book_visuals] تم إنشاء خلفية بديلة بمزاج '{mood}': {output_path}")
    return output_path


def fetch_all_book_assets(title: str, author: str, mood: str, english_title: str = None) -> dict:
    cover_path = os.path.join(ASSETS_DIR, "cover.jpg")
    background_path = os.path.join(ASSETS_DIR, "background.jpg")

    search_title = english_title or title

    # نبحث أولاً بالاسم الإنجليزي وحده (بدون اسم الكاتب) لتفادي كسر
    # المطابقة عند خلط لغتين مختلفتين بنفس نص البحث
    cover = fetch_book_cover(search_title, "", cover_path)
    if not cover:
        cover = fetch_book_cover(search_title, author, cover_path)
    if not cover:
        cover = fetch_google_books_cover(search_title, "", cover_path)
    if not cover:
        cover = create_placeholder_cover(title, mood, cover_path)

    background = fetch_background_image(mood, background_path)
    if not background:
        background = create_placeholder_background(mood, background_path)

    return {"cover": cover, "background": background}


if __name__ == "__main__":
    result = fetch_all_book_assets(
        "العادات الذرية", "جيمس كلير", "motivational", english_title="Atomic Habits"
    )
    print(result)
