from flask import Flask, request, jsonify
from flask_cors import CORS
import paramiko
import json
import os
import time
import requests

app = Flask(__name__)
CORS(app)

# SFTP настройки
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")
REMOTE_FILE = "/home/container/tlmodssuggestions.json"

# Пароль админа
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "tl-358856")

# Telegram
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TG_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID")

# Discord Webhook
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

cache_data = None


# ---------------- SFTP ----------------

def get_sftp():
    transport = paramiko.Transport((SFTP_HOST, 2022))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    return paramiko.SFTPClient.from_transport(transport), transport


def load_data():
    global cache_data
    try:
        sftp, t = get_sftp()
        with sftp.open(REMOTE_FILE, "r") as f:
            cache_data = json.load(f)
        sftp.close()
        t.close()
    except Exception as e:
        print(f"Error loading: {e}")
        cache_data = []


def save_data():
    try:
        sftp, t = get_sftp()
        with sftp.open(REMOTE_FILE, "w") as f:
            f.write(json.dumps(cache_data, indent=2, ensure_ascii=False))
        sftp.close()
        t.close()
    except Exception as e:
        print(f"Error saving: {e}")


# ---------------- Telegram ----------------

def send_tg_notification(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    if TG_THREAD_ID:
        payload["message_thread_id"] = TG_THREAD_ID

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")


# ---------------- Discord Webhook ----------------

def send_discord_webhook(message):
    if not DISCORD_WEBHOOK_URL:
        print("ОШИБКА DISCORD: Не задан DISCORD_WEBHOOK_URL!")
        return
    
    # Добавляем разделитель ─────────────── только для сообщений в Discord
    message_with_divider = f"{message}\n\n───────────────"
    
    # Заменяем домен на canary, чтобы обходить блокировку Cloudflare на Render
    url = DISCORD_WEBHOOK_URL.replace("discord.com", "canary.discord.com")

    payload = {
        "content": message_with_divider
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"Ответ Discord: Status {res.status_code}, Response: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки в Discord: {e}")


# ---------------- API ----------------

@app.route("/list", methods=["GET"])
def list_mods():
    if cache_data is None:
        load_data()
    return jsonify(cache_data)


@app.route("/add", methods=["POST"])
def add_mod():
    if cache_data is None:
        load_data()

    body = request.json or {}
    link = body.get("link")
    desc = body.get("desc", "")

    if not link:
        return jsonify({"error": "No link provided"}), 400

    new_id = int(time.time())

    new_item = {
        "id": new_id,
        "link": link,
        "desc": desc,
        "status": "pending"
    }

    cache_data.append(new_item)
    save_data()

    return jsonify({"status": "ok"})


@app.route("/admin_action", methods=["POST"])
def admin_action():
    global cache_data
    body = request.json or {}

    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Auth"}), 403

    if cache_data is None:
        load_data()

    target_id = str(body.get("id"))
    action = body.get("action")
    reason = body.get("reason", "")
    comment = body.get("comment", "")

    for m in cache_data:
        if str(m.get("id")) == target_id:

            if action == "approve":
                m["status"] = "approved"
                
                # Telegram
                tg_msg = f"✅ *Мод одобрен!*\n\n🔗 [Открыть мод]({m['link']})\n📝 Описание: {m['desc']}"
                send_tg_notification(tg_msg)

                # Discord
                ds_msg = f"✅ **Мод одобрен!**\n\n🔗 Ссылка: {m['link']}\n📝 Описание: {m['desc']}"
                send_discord_webhook(ds_msg)

            elif action == "reject":
                m["status"] = "rejected"
                m["reason"] = reason
                
                # Telegram
                tg_msg = f"❌ *Мод отклонён*\n\n🔗 [Открыть мод]({m['link']})\n🚫 Причина: {reason}"
                send_tg_notification(tg_msg)

                # Discord
                ds_msg = f"❌ **Мод отклонён**\n\n🔗 Ссылка: {m['link']}\n🚫 Причина: {reason}"
                send_discord_webhook(ds_msg)

            elif action == "set_comment":
                m["comment"] = comment

            elif action == "delete":
                cache_data = [mod for mod in cache_data if str(mod.get("id")) != target_id]
                save_data()
                return jsonify({"status": "ok"})

            break

    save_data()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    load_data()
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
