"""
script_maker.py
================
ينتج تلخيصاً شاملاً وعميقاً لكتاب معيّن باللغة العربية، بأسلوب سردي قوي
وجذاب، مقسّماً إلى مشاهد متتالية تغطي كل الكتاب.
"""

import os
import json
import re
import time

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ضع_مفتاح_Gemini_هنا")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ضع_مفتاح_OpenAI_هنا")

GEMINI_MODEL = "gemini-3.6-flash"
OPENAI_MODEL = "gpt-4o-mini"

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
SCRIPT_JSON_PATH = os.path.join(TEMP_DIR, "script.json")

VALID_MOODS = {"hopeful", "dark", "mysterious", "sad", "motivational", "neutral"}


def build_prompt(book_title: str, num_scenes: int = 20) -> str:
    prompt = f"""
أنت خبير في تلخيص الكتب وصناعة محتوى تعليمي جذاب لقناة "تلخيص كتب" ناجحة
على يوتيوب. أسلوبك قصصي قوي وحيوي، ليس جافاً أو أكاديمياً — تشرح الأفكار
بأمثلة وقصص وتشويق، بحيث لا يشعر المستمع بالملل أبداً رغم طول المحتوى.

المطلوب: لخّص كتاب "{book_title}" تلخيصاً شاملاً وعميقاً باللغة العربية
الفصحى المبسّطة، بحيث يخرج المستمع فاهماً كل الأفكار الأساسية بالكتاب
وكأنه قرأه فعلاً.

قواعد صارمة لتجنّب الملل:
- ابدأ بمقدمة خطافة قوية: لماذا هذا الكتاب مهم؟ ما المشكلة التي يحلّها؟
- بعدها نبذة قصيرة وشيّقة عن الكاتب (من هو، ولماذا يستحق أن نسمع له).
- غطِّ كل فكرة رئيسية أو فصل بمشهد منفصل، واشرحها بمثال واقعي أو قصة
  قصيرة تجعلها ملموسة، لا مجرد سرد نظري.
- نوّع أسلوب الانتقال بين المشاهد: أحياناً بسؤال يشد الانتباه، أحياناً
  بمقارنة، أحياناً بقصة قصيرة، لتفادي الرتابة.
- اختم بخاتمة تطبيقية: ما الذي يجب أن يفعله المستمع الآن بعد سماع هذا؟
  لخّص أهم 3-5 دروس عملية قابلة للتطبيق فوراً.
- هذا فيديو طويل يستهدف نحو 30 دقيقة، لذا يجب تغطية الكتاب بعمق كافٍ
  عبر {num_scenes} مشهداً، كل مشهد فيه فقرة متوسطة الطول (5-8 جمل).
- اكتب كل نص "narration" كسطر واحد متصل بدون فواصل أسطر داخله.

بالإضافة للمشاهد، حدّد:
- "book_title": اسم الكتاب كما تعرفه (بالعربية أو مترجم إن كان معروفاً).
- "author": اسم مؤلف الكتاب.
- "mood": كلمة إنجليزية واحدة فقط تصف الجو العام لأفكار الكتاب، تُختار
  من هذه القائمة فقط: hopeful, dark, mysterious, sad, motivational, neutral

أخرج النتيجة **فقط** بصيغة JSON صالحة (بدون أي نص إضافي قبلها أو بعدها)
على الشكل التالي بالضبط:

{{
  "book_title": "...",
  "author": "...",
  "mood": "...",
  "scenes": [
    {{"narration": "..."}},
    {{"narration": "..."}}
  ]
}}
"""
    return prompt.strip()


def generate_with_gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.85,
            "max_output_tokens": 32768,
        },
    )
    return response.text


def generate_with_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "أنت خبير تلخيص كتب ومحتوى تعليمي جذاب."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def extract_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip("`\n ")

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        last_complete = cleaned.rfind('"},')
        if last_complete != -1:
            repaired = cleaned[: last_complete + 2] + "]}"
            return json.loads(repaired)
        raise


def generate_script(book_title: str, num_scenes: int = 20, max_retries: int = 3) -> dict:
    prompt = build_prompt(book_title, num_scenes)

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

            result = extract_json(raw_text)

            scenes = result.get("scenes")
            if not isinstance(scenes, list) or len(scenes) == 0:
                raise ValueError("الرد لا يحتوي على قائمة مشاهد صالحة.")

            for scene in scenes:
                if "narration" not in scene:
                    raise ValueError("أحد المشاهد يفتقد لحقل narration.")

            if result.get("mood") not in VALID_MOODS:
                result["mood"] = "neutral"

            result.setdefault("book_title", book_title)
            result.setdefault("author", "غير معروف")

            with open(SCRIPT_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(
                f"[script_maker] تم إنتاج تلخيص '{result['book_title']}' "
                f"({len(scenes)} مشهداً، مزاج: {result['mood']})."
            )
            return result

        except Exception as e:
            last_error = e
            print(f"[script_maker] فشلت المحاولة {attempt}: {e}")
            time.sleep(2)

    raise RuntimeError(f"فشل إنتاج التلخيص بعد {max_retries} محاولات: {last_error}")


if __name__ == "__main__":
    result = generate_script("Atomic Habits", num_scenes=6)
    print(json.dumps(result, ensure_ascii=False, indent=2))
