
# config.py - ضع بياناتك هنا
# ⚠️ لا تشارك هذا الملف على GitHub مع بيانات حقيقية!

import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")  # ID الأدمن الرئيسي
WEB_DOMAIN = os.environ.get("WEB_DOMAIN", "") # رابط المشروع على Vercel
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "") # سر الويب هوك
