"""
main.py
=======
الملف الرئيسي (Orchestrator) الذي يدير خط إنتاج فيديو تلخيص كتاب كاملاً.

طريقة التشغيل:
    python main.py --book "اسم الكتاب" --scenes 20
"""

import os
import sys
import shutil
import argparse
import traceback
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import script_maker
import voice_maker
import book_visuals
import music_maker
import video_editor
import drive_uploader

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def parse_args():
    parser = argparse.ArgumentParser(
        description="نظام آلي لإنتاج فيديو تلخيص كتاب ورفعه إلى Google Drive"
    )
    parser.add_argument(
        "--book", type=str, required=True, help="اسم الكتاب المراد تلخيصه"
    )
    parser.add_argument(
        "--scenes",
        type=int,
        default=20,
        help="عدد مشاهد التلخيص (20 تقريباً = فيديو 25-30 دقيقة)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="الاحتفاظ بالملفات المؤقتة بعد الانتهاء (لأغراض التصحيح)",
    )
    return parser.parse_args()


def clean_temp_files():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print("[main] تم مسح الملفات المؤقتة بنجاح.")


def run_pipeline(book_title: str, num_scenes: int, keep_temp: bool = False):
    start_time = datetime.now()
    print("=" * 70)
    print("[main] بدء إنتاج فيديو تلخيص كتاب")
    print(f"[main] الكتاب: {book_title}")
    print(f"[main] عدد المشاهد: {num_scenes}")
    print("=" * 70)

    try:
        print("\n[main] (1/6) تلخيص الكتاب...")
        script_data = script_maker.generate_script(book_title, num_scenes=num_scenes)
        scenes = script_data["scenes"]
        author = script_data["author"]
        mood = script_data["mood"]
        resolved_title = script_data["book_title"]
        english_title = script_data.get("english_title", resolved_title)

        print("\n[main] (2/6) توليد التعليق الصوتي...")
        audio_paths = voice_maker.generate_all_voices(scenes)

        print("\n[main] (3/6) جلب غلاف الكتاب وصورة الخلفية...")
        assets = book_visuals.fetch_all_book_assets(
            resolved_title, author, mood, english_title=english_title
        )

        print("\n[main] (4/6) جلب موسيقى خلفية...")
        music_path = music_maker.fetch_background_music(
            os.path.join(TEMP_DIR, "music", "background.mp3"), mood=mood
        )

        print("\n[main] (5/6) بناء الفيديو النهائي...")
        final_video_path = video_editor.create_final_video(
            audio_paths,
            assets["background"],
            assets["cover"],
            music_path=music_path,
        )

        print("\n[main] (6/6) رفع الفيديو إلى Google Drive...")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_title = "".join(c if c.isalnum() else "_" for c in resolved_title)[:40]
        upload_name = f"{safe_title}_{timestamp}.mp4"
        drive_link = drive_uploader.upload_video(final_video_path, file_name=upload_name)

        print("\n" + "=" * 70)
        print("[main] اكتمل الإنتاج بنجاح!")
        print(f"[main] الكتاب: {resolved_title} — تأليف: {author}")
        print(f"[main] رابط الفيديو على Google Drive: {drive_link}")
        print("=" * 70)

        if not keep_temp:
            clean_temp_files()

        elapsed = datetime.now() - start_time
        print(f"[main] الوقت الإجمالي المستغرق: {elapsed}")

        return drive_link

    except Exception as e:
        print("\n[main] حدث خطأ أثناء تنفيذ خط الإنتاج:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(book_title=args.book, num_scenes=args.scenes, keep_temp=args.keep_temp)
