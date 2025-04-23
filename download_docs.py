import os
import sys
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone = os.getenv("TELEGRAM_PHONE")
channel = sys.argv[1] if len(sys.argv) > 1 else None

if not channel:
    print("❌ Укажи ссылку на канал при запуске, например:")
    print("   python3 download_docs.py https://t.me/example_channel")
    sys.exit(1)

# Папки и лог
download_dir = "./downloads"
log_file_path = "download.log"
os.makedirs(download_dir, exist_ok=True)

client = TelegramClient("anon", api_id, api_hash)

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

async def download_documents():
    await client.start(phone=phone)
    log(f"🔗 Начинаем загрузку из канала: {channel}")

    count = 0
    skipped = 0

    async for message in client.iter_messages(channel):
        if message.media and isinstance(message.media, MessageMediaDocument):
            filename = message.file.name or f"{message.id}.pdf"

            if not filename.lower().endswith(".pdf"):
                continue

            save_path = os.path.join(download_dir, filename)

            if os.path.exists(save_path):
                log(f"⏩ Уже есть: {filename}")
                skipped += 1
                continue

            log(f"📄 Скачиваем: {filename}")
            await client.download_media(message, save_path)
            count += 1

    log(f"✅ Готово: скачано {count}, пропущено {skipped}")

# Запуск
with client:
    client.loop.run_until_complete(download_documents())
