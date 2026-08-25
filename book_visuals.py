"""
book_visuals.py
================
يجلب صورتين لكل فيديو تلخيص كتاب:
    1) غلاف الكتاب — عبر Open Library (مجاني بالكامل، بدون أي مفتاح API)
    2) صورة خلفية ثابتة تناسب مزاج الكتاب — عبر Pexels Photos API
"""

import os
import urllib.parse
import requests

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


def fetch_book_cover(title: str, author: str, output_path: str) -> str:
    try:
        query = f"{title} {author}".strip()
        search_url = "https://openlibrary.org/search.json"
        params = {"q": query, "limit": 3}

        response = requests.get(search_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        cover_id = None
        for doc in docs:
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

        print(f"[book_visuals] تم تحميل غلاف الكتاب: {output_path}")
        return output_path

    except Exception as e:
        print(f"[book_visuals] فشل جلب الغلاف: {e}")
        return None


def fetch_google_books_cover(title: str, author: str, output_path: str) -> str:
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
        print(f"[book_visuals] فشل جلب الغلاف من Google Books أيضاً: {e}")
        return None


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


def fetch_all_book_assets(title: str, author: str, mood: str) -> dict:
    cover_path = os.path.join(ASSETS_DIR, "cover.jpg")
    background_path = os.path.join(ASSETS_DIR, "background.jpg")

    cover = fetch_book_cover(title, author, cover_path)
    if not cover:
        cover = fetch_google_books_cover(title, author, cover_path)

    background = fetch_background_image(mood, background_path)

    return {"cover": cover, "background": background}


if __name__ == "__main__":
    result = fetch_all_book_assets("Atomic Habits", "James Clear", "motivational")
    print(result)
