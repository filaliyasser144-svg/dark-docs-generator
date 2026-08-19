"""
script_maker.py
================
يتولى هذا الملف إنتاج سيناريو وثائقي بأسلوب غموض/جريمة (Dark Crime Mystery)
باستخدام Gemini API (افتراضياً) مع دعم اختياري لـ OpenAI API كبديل.

المخرجات:
    قائمة (list) من القواميس (dict)، كل عنصر يمثل "مشهداً" ويحتوي على:
        - "narration": نص التعليق الصوتي لهذا المشهد (بالعربية الفصحى الدرامية)
        - "image_prompt": وصف إنجليزي سينمائي مظلم لتوليد صورة المشهد

يتم حفظ النتيجة أيضاً في ملف JSON مؤقت (temp/script.json) ليستخدمه بقية النظام.
"""

import os
import json
import re
import time

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

# ---------------------- ضع مفاتيح الـ API هنا -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ضع_مفتاح_Gemini_هنا")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ضع_مفتاح_OpenAI_هنا")
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-3.6-flash"
OPENAI_MODEL = "gpt-4o-mini"

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
SCRIPT_JSON_PATH = os.path.join(TEMP_DIR, "script.json")


def build_prompt(topic: str, num_scenes: int = 8) -> str:
    prompt = f"""
أنت كاتب سيناريو محترف متخصص في صناعة الأفلام الوثائقية الغامضة والجنائية
(True Crime / Mystery Documentary) باللغة العربية الفصحى مع تبسيط درامي جذاب.

المطلوب: اكتب سيناريو وثائقي عن الموضوع التالي:
"{topic}"

شروط الأسلوب:
- ابدأ بمقدمة خطافة صادمة (Dramatic Hook) تشد المستمع من الثانية الأولى.
- استخدم أسلوب سرد التحقيق البوليسي: غموض، توتر، تفاصيل دقيقة، تشويق تصاعدي.
- نبرة الكتابة: وقورة، عميقة، هادئة، تبعث على الترقب.
- قسّم السيناريو إلى {num_scenes} مشاهد متتالية، كل مشهد يمثل حلقة في القصة.
- هذا فيديو وثائقي طويل (يستهدف 15-20 دقيقة)، لذا يجب أن يكون كل مشهد
  غنياً بالتفاصيل ومطوّلاً نسبياً، وليس مجرد جملة قصيرة عابرة.

لكل مشهد يجب أن توفر:
1) "narration": نص التعليق الصوتي بالعربية الفصحى (8-12 جملة طويلة
   ومترابطة، تروي تفاصيل غنية ودقيقة عن هذا الجزء من القصة).
2) "image_prompt": وصف بصري بالإنجليزية لمشهد سينمائي مظلم يلائم هذا الجزء
   من القصة، يتضمن: cinematic lighting, dark and moody atmosphere,
   dramatic camera angle, investigation room / crime scene / night street
   / screens (حسب سياق المشهد), photorealistic, high detail, 4k.

أخرج النتيجة **فقط** بصيغة JSON صالحة (بدون أي نص إضافي قبلها أو بعدها)
على الشكل التالي:

[
  {{"narration": "...", "image_prompt": "..."}},
  {{"narration": "...", "image_prompt": "..."}}
]
"""
    return prompt.strip()


def generate_with_gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.9,
            "max_output_tokens": 8192,
        },
    )
    return response.text


def generate_with_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "أنت كاتب سيناريوهات وثائقية جنائية محترف."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def extract_json(raw_text: str):
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip("`\n ")

    match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    return json.loads(cleaned)


def generate_script(topic: str, num_scenes: int = 8, max_retries: int = 3):
    prompt = build_prompt(topic, num_scenes)

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[script_maker] المحاولة {attempt}/{max_retries} - المزود: {AI_PROVIDER}")

            if AI_PROVIDER == "gemini":
                raw_text = generate_with_gemini(prompt)
            elif AI_PROVIDER == "openai":
                raw_text = generate_with_openai(prompt)
            else:
                raise ValueError(f"مزود غير مدعوم: {AI_PROVIDER}")

            scenes = extract_json(raw_text)

            if not isinstance(scenes, list) or len(scenes) == 0:
                raise ValueError("الرد لا يحتوي على قائمة مشاهد صالحة.")

            for scene in scenes:
                if "narration" not in scene or "image_prompt" not in scene:
                    raise ValueError("أحد المشاهد يفتقد لحقل narration أو image_prompt.")

            with open(SCRIPT_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(scenes, f, ensure_ascii=False, indent=2)

            print(f"[script_maker] تم إنتاج {len(scenes)} مشهداً بنجاح.")
            return scenes

        except Exception as e:
            last_error = e
            print(f"[script_maker] فشلت المحاولة {attempt}: {e}")
            time.sleep(2)

    raise RuntimeError(f"فشل إنتاج السيناريو بعد {max_retries} محاولات: {last_error}")


if __name__ == "__main__":
    test_topic = "اختفاء غامض لطالبة جامعية في مدينة أوروبية صغيرة"
    result = generate_script(test_topic, num_scenes=5)
    print(json.dumps(result, ensure_ascii=False, indent=2))
