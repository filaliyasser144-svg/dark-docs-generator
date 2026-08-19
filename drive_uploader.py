"""
drive_uploader.py
==================
يرفع ملف الفيديو النهائي تلقائياً إلى مجلد محدد على Google Drive،
باستخدام بيانات اعتماد OAuth الخاصة بحسابك الشخصي (وليس Service Account).

السبب: حسابات الخدمة (Service Account) على حسابات Gmail العادية لا تملك
مساحة تخزين خاصة بها، فيفشل الرفع برسالة storageQuotaExceeded حتى لو
كان حسابك الشخصي يملك مساحة كبيرة. الحل هو الرفع "نيابة عنك" مباشرة
عبر OAuth، فيُحتسب الملف على مساحتك الحقيقية.

المتطلبات:
    1) OAuth Client ID (نوع Desktop app) من Google Cloud Console.
    2) Refresh Token يُولَّد مرة واحدة فقط (راجع تعليمات README لطريقة
       توليده عبر Google Colab).
    3) المتغيرات البيئية التالية:
       - GOOGLE_OAUTH_CLIENT_ID
       - GOOGLE_OAUTH_CLIENT_SECRET
       - GOOGLE_OAUTH_REFRESH_TOKEN
       - GOOGLE_DRIVE_FOLDER_ID
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------- ضع بيانات الاعتماد هنا -----------------------------
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "ضع_Client_ID_هنا")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "ضع_Client_Secret_هنا")
REFRESH_TOKEN = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "ضع_Refresh_Token_هنا")

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "ضع_معرف_مجلد_Google_Drive_هنا")
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_drive_service():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    creds.refresh(Request())

    service = build("drive", "v3", credentials=creds)
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
