"""
drive_uploader.py
==================
يرفع ملف الفيديو النهائي تلقائياً إلى مجلد محدد على Google Drive،
باستخدام حساب خدمة (Service Account) عبر Google Drive API.

المتطلبات:
    1) إنشاء مشروع على Google Cloud Console وتفعيل Google Drive API.
    2) إنشاء Service Account وتنزيل ملف JSON الخاص بمفاتيحه.
    3) مشاركة المجلد الهدف على Drive مع بريد الـ Service Account
       (الموجود داخل ملف الـ JSON) بصلاحية "Editor".
    4) وضع مسار ملف الـ JSON في المتغير SERVICE_ACCOUNT_FILE أدناه،
       أو تمريره عبر متغير بيئة GOOGLE_SERVICE_ACCOUNT_FILE.
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------- ضع بيانات الاعتماد هنا -----------------------------
SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "ضع_مسار_ملف_service_account.json_هنا"
)

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "ضع_معرف_مجلد_Google_Drive_هنا")
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"ملف بيانات اعتماد Google غير موجود: {SERVICE_ACCOUNT_FILE}\n"
            "تأكد من ضبط GOOGLE_SERVICE_ACCOUNT_FILE بشكل صحيح."
        )

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    return service


def upload_video(file_path: str, folder_id: str = None, file_name: str = None) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ملف الفيديو غير موجود: {file_path}")

    folder_id = folder_id or DRIVE_FOLDER_ID
    file_name = file_name or os.path.basename(file_path)

    service = get_drive_service()

    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)

    print(f"[drive_uploader] بدء رفع الملف: {file_name} ...")

    uploaded_file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )

    file_id = uploaded_file.get("id")
    file_link = uploaded_file.get("webViewLink")

    print(f"[drive_uploader] تم رفع الفيديو بنجاح. المعرف: {file_id}")
    print(f"[drive_uploader] رابط المشاهدة: {file_link}")

    return file_link


if __name__ == "__main__":
    video_path = os.path.join(
        os.path.dirname(__file__), "output", "final_video.mp4"
    )
    link = upload_video(video_path)
    print("رابط الفيديو المرفوع:", link)
