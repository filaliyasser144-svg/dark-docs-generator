"""
voice_maker.py
==============
يحوّل نصوص السيناريو (narration لكل مشهد) إلى ملفات صوتية باستخدام
Edge-TTS، وهي خدمة تحويل نص إلى صوت من مايكروسوفت (تعمل خلف كواليس
متصفح Edge / تطبيق Read Aloud)، وهي **مجانية بالكامل ولا تتطلب أي
مفتاح API أو تسجيل**.

جودة الأصوات عالية جداً وتدعم العربية بشكل ممتاز، وفيها أصوات ذكورية
عميقة تناسب طابع "الراوي الوثائقي".

المخرجات:
    - ملف صوتي منفصل لكل مشهد داخل temp/audio/scene_XX.mp3
    - قائمة بمسارات هذه الملفات (بنفس ترتيب المشاهد)
"""

import os
import json
import asyncio
import edge_tts

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
AUDIO_DIR = os.path.join(TEMP_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# =========================================================================
#  اختيار الصوت (Voice) — مجاني بالكامل، بدون مفتاح API
# =========================================================================
VOICE_NAME = os.getenv("EDGE_TTS_VOICE", "ar-SA-HamedNeural")

SPEECH_RATE = os.getenv("EDGE_TTS_RATE", "-8%")
SPEECH_PITCH = os.getenv("EDGE_TTS_PITCH", "-5Hz")


async def _synthesize_async(text: str, output_path: str):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE_NAME,
        rate=SPEECH_RATE,
        pitch=SPEECH_PITCH,
    )
    await communicate.save(output_path)


def synthesize_scene(text: str, output_path: str, max_retries: int = 3) -> str:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[voice_maker] توليد صوت للمقطع... (محاولة {attempt})")
            asyncio.run(_synthesize_async(text, output_path))

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise RuntimeError("تم إنشاء ملف صوتي فارغ أو غير موجود.")

            return output_path

        except Exception as e:
            last_error = e
            print(f"[voice_maker] فشلت المحاولة {attempt}: {e}")

    raise RuntimeError(f"فشل توليد الصوت بعد {max_retries} محاولات: {last_error}")


def generate_all_voices(scenes: list) -> list:
    audio_paths = []

    for idx, scene in enumerate(scenes, start=1):
        narration = scene["narration"]
        output_path = os.path.join(AUDIO_DIR, f"scene_{idx:02d}.mp3")

        synthesize_scene(narration, output_path)
        audio_paths.append(output_path)
        print(f"[voice_maker] تم إنشاء: {output_path}")

    return audio_paths


if __name__ == "__main__":
    script_path = os.path.join(TEMP_DIR, "script.json")
    if not os.path.exists(script_path):
        raise FileNotFoundError(
            "لم يتم العثور على temp/script.json. شغّل script_maker.py أولاً."
        )

    with open(script_path, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    paths = generate_all_voices(scenes_data)
    print("تم إنشاء الملفات الصوتية التالية:")
    for p in paths:
        print(" -", p)
