"""
voice_maker.py
==============
يحوّل نصوص السيناريو إلى تعليق صوتي احترافي.

الأولوية: **Gemini TTS** (يستخدم نفس مفتاح Gemini الموجود عندك أصلاً،
بدون أي إعداد إضافي) — جودته طبيعية جداً وقريبة من صوت بشري حقيقي.

في حال فشل Gemini TTS لأي سبب، ينتقل النظام تلقائياً لبديل احتياطي:
Edge-TTS (مجاني، بدون مفتاح).

المخرجات:
    - ملف صوتي منفصل لكل مشهد داخل temp/audio/scene_XX.mp3
    - قائمة بمسارات هذه الملفات (بنفس ترتيب المشاهد)
"""

import os
import json
import time
import base64
import wave
import asyncio
import requests

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
AUDIO_DIR = os.path.join(TEMP_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ضع_مفتاح_Gemini_هنا")

GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_VOICE_NAME = os.getenv("GEMINI_VOICE_NAME", "Charon")

GEMINI_TTS_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

STYLE_INSTRUCTION = (
    "اقرأ النص التالي بصوت راوي وثائقي وقور، هادئ، عميق، وبطيء الإيقاع، "
    "يبعث على الغموض والترقب، بأسلوب أفلام الجرائم الوثائقية:\n\n"
)


def _save_pcm_as_wav(pcm_data: bytes, output_path_wav: str, sample_rate: int = 24000):
    with wave.open(output_path_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def synthesize_with_gemini(text: str, output_path: str) -> bool:
    try:
        payload = {
            "contents": [{"parts": [{"text": STYLE_INSTRUCTION + text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE_NAME}
                    }
                },
            },
        }

        response = requests.post(GEMINI_TTS_URL, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()

        audio_b64 = (
            data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        )
        pcm_data = base64.b64decode(audio_b64)

        wav_path = output_path.replace(".mp3", ".wav")
        _save_pcm_as_wav(pcm_data, wav_path)
        os.replace(wav_path, output_path)

        return True

    except Exception as e:
        print(f"[voice_maker] فشل Gemini TTS: {e}")
        return False


EDGE_VOICE_NAME = os.getenv("EDGE_TTS_VOICE", "ar-SA-HamedNeural")
EDGE_SPEECH_RATE = os.getenv("EDGE_TTS_RATE", "-8%")
EDGE_SPEECH_PITCH = os.getenv("EDGE_TTS_PITCH", "-5Hz")


async def _synthesize_edge_async(text: str, output_path: str):
    import edge_tts

    communicate = edge_tts.Communicate(
        text=text,
        voice=EDGE_VOICE_NAME,
        rate=EDGE_SPEECH_RATE,
        pitch=EDGE_SPEECH_PITCH,
    )
    await communicate.save(output_path)


def synthesize_with_edge(text: str, output_path: str) -> bool:
    try:
        asyncio.run(_synthesize_edge_async(text, output_path))
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"[voice_maker] فشل Edge-TTS أيضاً: {e}")
        return False


def synthesize_scene(text: str, output_path: str, max_retries: int = 2) -> str:
    for attempt in range(1, max_retries + 1):
        print(f"[voice_maker] توليد صوت عبر Gemini TTS... (محاولة {attempt})")
        if synthesize_with_gemini(text, output_path):
            print(f"[voice_maker] نجح Gemini TTS: {output_path}")
            return output_path
        time.sleep(2)

    print("[voice_maker] التبديل للبديل الاحتياطي Edge-TTS...")
    if synthesize_with_edge(text, output_path):
        print(f"[voice_maker] نجح Edge-TTS (احتياطي): {output_path}")
        return output_path

    raise RuntimeError(f"فشل توليد الصوت بكل الطرق المتاحة للملف: {output_path}")


def generate_all_voices(scenes: list) -> list:
    audio_paths = []

    for idx, scene in enumerate(scenes, start=1):
        narration = scene["narration"]
        output_path = os.path.join(AUDIO_DIR, f"scene_{idx:02d}.mp3")

        synthesize_scene(narration, output_path)
        audio_paths.append(output_path)

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
