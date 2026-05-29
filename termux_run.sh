#!/data/data/com.termux/files/usr/bin/bash

echo "[+] Installing requirements..."
pkg update && pkg upgrade -y
pkg install python git -y
pip install flask requests python-dotenv gunicorn

echo "[+] Setting up environment..."
export TELEGRAM_BOT_TOKEN="8645238541:AAF_THZ08LqIiV8MkxmosktWt3CneAX_bM4"
export ADMIN_CHAT_ID="7968208362"
export WEB_DOMAIN="https://mohmmadsedeg30-design.github.io/camera-awareness-bot-private"

echo "[+] Starting Camera Awareness Bot..."
python app.py
