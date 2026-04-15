from flask import Flask, request, jsonify
from flask_cors import CORS
import paramiko
import json
import os
import time

app = Flask(__name__)
CORS(app)

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")
ADMIN_PASSWORD = "tl-358856"
REMOTE_FILE = "/home/container/tlmodssuggestions.json"

cache_data = None

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
    except:
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

@app.route("/list", methods=["GET"])
def list_mods():
    if cache_data is None: load_data()
    return jsonify(cache_data)

@app.route("/add", methods=["POST"])
def add_mod():
    if cache_data is None: load_data()
    body = request.json
    new_id = int(time.time())
    new_item = {
        "id": new_id,
        "link": body.get("link"),
        "desc": body.get("desc", ""),
        "status": "pending"
    }
    cache_data.append(new_item)
    save_data()
    return jsonify({"status": "ok"})

@app.route("/admin_action", methods=["POST"])
def admin_action():
    global cache_data
    body = request.json
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Auth"}), 403

    if cache_data is None: load_data()
    
    target_id = str(body.get("id"))
    action = body.get("action")
    reason = body.get("reason", "")
    comment = body.get("comment", "") # Новое поле для комментария

    if action == "delete":
        cache_data = [m for m in cache_data if str(m.get("id")) != target_id]
    else:
        for m in cache_data:
            if str(m.get("id")) == target_id:
                if action == "approve":
                    m["status"] = "approved"
                elif action == "reject":
                    m["status"] = "rejected"
                    m["reason"] = reason
                elif action == "set_comment": # Новое действие для обновления комментария
                    m["comment"] = comment
    
    save_data()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=10000)
    
