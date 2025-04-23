import os
import io
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# Загрузка .env
load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone = os.getenv("TELEGRAM_PHONE")
sheet_id = os.getenv("GOOGLE_SHEET_ID")
credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Лог
log_file_path = "upload.log"
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# Получение списка каналов из таблицы
def get_channel_links():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        sheet = gspread.authorize(creds).open_by_key(sheet_id).sheet1
        rows = sheet.get_all_values()[1:]
        return [row[1] for row in rows if len(row) > 1 and row[1].startswith("https://t.me/")]
    except Exception as e:
        log(f"❌ Ошибка подключения к таблице: {e}")
        return []

# Инициализация клиента Google Drive
def init_drive_client():
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

drive_service = init_drive_client()

# Проверка, существует ли файл в папке
def file_exists_in_drive(file_name):
    query = f"name='{file_name}' and '{drive_folder_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    return len(response.get('files', [])) > 0

# Загрузка в Google Drive
def upload_to_drive(file_name, file_content):
    media = MediaIoBaseUpload(file_content, mimetype='application/pdf', resumable=False)
    drive_service.files().create(
        media_body=media,
        body={
            'name': file_name,
            'parents': [drive_folder_id]
        },
        fields='id'
    ).execute()
    log(f"☁️ Загружен в Drive: {file_name}")

# Основной блок загрузки
async def download_from_channel(channel, client):
    log(f"🔗 Обработка канала: {channel}")
    count, skipped = 0, 0

    async for message in client.iter_messages(channel):
        if message.media and isinstance(message.media, MessageMediaDocument):
            filename = message.file.name or f"{message.id}.pdf"
            if not filename.lower().endswith(".pdf"):
                continue

            if file_exists_in_drive(filename):
                log(f"⏩ Уже в Google Drive: {filename}")
                skipped += 1
                continue

            log(f"📄 Скачиваем в память: {filename}")
            buffer = io.BytesIO()
            await client.download_media(message, buffer)
            buffer.seek(0)

            upload_to_drive(filename, buffer)
            count += 1

    log(f"✅ {channel}: загружено {count}, пропущено {skipped}")

# Запуск
async def run_all():
    async with TelegramClient("anon", api_id, api_hash) as client:
        await client.start(phone=phone)
        links = get_channel_links()
        if not links:
            log("⚠️ Список каналов пуст.")
            return
        for link in links:
            try:
                await download_from_channel(link, client)
            except Exception as e:
                log(f"❌ Ошибка в {link}: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all())
