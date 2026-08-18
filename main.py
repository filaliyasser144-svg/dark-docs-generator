"""
main.py
=======
الملف الرئيسي (Orchestrator) الذي يدير خط الإنتاج الكامل بالترتيب:

    1) script_maker   -> كتابة السيناريو + أوامر الصور
    2) voice_maker     -> تحويل النصوص إلى تعليق صوتي
    3) visuals_maker    -> توليد الصور السينمائية
    4) video_editor     -> مونتاج الفيديو النهائي (Ken Burns + دمج صوت)
    5) drive_uploader   -> رفع الفيديو النهائي إلى Google Drive
    6) تنظيف الملفات المؤقتة بعد نجاح الرفع

طريقة التشغيل:
    python main.py --topic "موضوع الحلقة هنا" --scenes 8

أو اتركه بدون --topic ليستخدم موضوعاً افتراضياً.
"""

import os
import sys
import shutil
import argparse
import traceback
import random
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import script_maker
import voice_maker
import visuals_maker
import video_editor
import drive_uploader

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

TOPICS_POOL = [
    "جريمة غامضة لم تُحل حتى اليوم داخل بلدة صغيرة",
    "اختفاء غامض لباحث علمي أثناء عمله الميداني",
    "قضية احتيال إلكتروني ضخمة هزّت شركة تقنية",
    "لغز اختفاء سفينة شحن في محيط مظلم",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="نظام آلي لإنتاج فيديو وثائقي غامض/جنائي ورفعه إلى Google Drive"
    )
    parser.add_argument(
        "--topic", type=str, default=None, help="موضوع الحلقة (نص عربي)"
    )
    parser.add_argument(
        "--scenes", type=int, default=8, help="عدد المشاهد المطلوبة في السيناريو"
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


def run_pipeline(topic: str, num_scenes: int, keep_temp: bool = False):
    start_time = datetime.now()
    print("=" * 70)
    print(f"[main] بدء إنتاج الفيديو الوثائقي")
    print(f"[main] الموضوع: {topic}")
    print(f"[main] عدد المشاهد: {num_scenes}")
    print("=" * 70)

    try:
        print("\n[main] (1/5) كتابة السيناريو...")
        scenes = script_maker.generate_script(topic, num_scenes=num_scenes)

        print("\n[main] (2/5) توليد التعليق الصوتي...")
        audio_paths = voice_maker.generate_all_voices(scenes)

        print("\n[main] (3/5) توليد الصور السينمائية...")
        image_paths = visuals_maker.generate_all_visuals(scenes)

        print("\n[main] (4/5) مونتاج الفيديو النهائي...")
        final_video_path = video_editor.create_final_video(
            scenes, image_paths, audio_paths
        )

        print("\n[main] (5/5) رفع الفيديو إلى Google Drive...")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        upload_name = f"documentary_{timestamp}.mp4"
        drive_link = drive_uploader.upload_video(
            final_video_path, file_name=upload_name
        )

        print("\n" + "=" * 70)
        print("[main] اكتمل الإنتاج بنجاح!")
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

    topic = args.topic or random.choice(TOPICS_POOL)

    run_pipeline(topic=topic, num_scenes=args.scenes, keep_temp=args.keep_temp)
