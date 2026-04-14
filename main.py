from flask import Flask, request, jsonify
from flask_cors import CORS
import paramiko
import json
import os
import time

app = Flask(__name__)
CORS(app)

# Конфигурация
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")
ADMIN_PASSWORD = "tl-358856"
REMOTE_FILE = "/home/container/tlmodssuggestions.json"

# Кэш в оперативной памяти
cache_data = None

def get_sftp():
    transport = paramiko.Transport((SFTP_HOST, 2022))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    return paramiko.SFTPClient.from_transport(transport), transport

def load_from_disk():
    global cache_data
    try:
        sftp, t = get_sftp()
        try:
            with sftp.open(REMOTE_FILE, "r") as f:
                cache_data = json.load(f)
        except:
            cache_data = []
        sftp.close()
        t.close()
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        cache_data = []

def save_to_disk():
    global cache_data
    try:
        sftp, t = get_sftp()
        with sftp.open(REMOTE_FILE, "w") as f:
            f.write(json.dumps(cache_data, indent=2))
        sftp.close()
        t.close()
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

@app.route("/list", methods=["GET"])
def list_mods():
    if cache_data is None: load_from_disk()
    return jsonify(cache_data)

@app.route("/add", methods=["POST"])
def add_mod():
    if cache_data is None: load_from_disk()
    
    body = request.json
    new_item = {
        "id": str(int(time.time() * 1000)), # Всегда строка
        "link": body.get("link"),
        "desc": body.get("desc", ""),
        "status": "pending"
    }
    cache_data.append(new_item)
    save_to_disk()
    return jsonify({"status": "ok"})

@app.route("/admin_action", methods=["POST"])
def admin_action():
    global cache_data
    if cache_data is None: load_from_disk()
    
    body = request.json
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403

    mod_id = str(body.get("id")) # Принудительно в строку
    action = body.get("action")

    if action == "delete":
        # Сравнение через str() для обхода проблем с форматом в JSON
        cache_data = [m for m in cache_data if str(m.get("id")) != mod_id]
    else:
        for m in cache_data:
            if str(m.get("id")) == mod_id:
                m["status"] = "approved" if action == "approve" else "rejected"

    save_to_disk()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    load_from_disk()
    app.run(host="0.0.0.0", port=10000)
