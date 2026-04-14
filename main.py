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

def sftp_connect():
    client = paramiko.Transport((SFTP_HOST, 2022))
    client.connect(username=SFTP_USER, password=SFTP_PASS)
    return client

def get_data(sftp):
    try:
        with sftp.open(REMOTE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(sftp, data):
    with sftp.open(REMOTE_FILE, "w") as f:
        f.write(json.dumps(data, indent=2))

@app.route("/list", methods=["GET"])
def list_mods():
    client = sftp_connect()
    sftp = paramiko.SFTPClient.from_transport(client)
    data = get_data(sftp)
    sftp.close()
    client.close()
    return jsonify(data)

@app.route("/add", methods=["POST"])
def add_mod():
    body = request.json
    client = sftp_connect()
    sftp = paramiko.SFTPClient.from_transport(client)
    data = get_data(sftp)
    
    new_mod = {
        "id": str(int(time.time() * 1000)),
        "link": body.get("link"),
        "desc": body.get("desc", ""),
        "status": "pending" # По умолчанию — на рассмотрении
    }
    data.append(new_mod)
    save_data(sftp, data)
    
    sftp.close()
    client.close()
    return jsonify({"status": "ok"})

@app.route("/admin_action", methods=["POST"])
def admin_action():
    body = request.json
    # Проверка пароля на уровне сервера — это важно!
    if body.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Wrong password"}), 403

    action = body.get("action") # 'approve', 'reject', 'delete'
    mod_id = body.get("id")

    client = sftp_connect()
    sftp = paramiko.SFTPClient.from_transport(client)
    data = get_data(sftp)

    if action == "delete":
        data = [m for m in data if m["id"] != mod_id]
    else:
        for m in data:
            if m["id"] == mod_id:
                m["status"] = "approved" if action == "approve" else "rejected"

    save_data(sftp, data)
    sftp.close()
    client.close()
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
