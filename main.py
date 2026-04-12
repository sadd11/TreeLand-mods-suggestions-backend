from flask import Flask, request, jsonify
import paramiko
import json
import os

app = Flask(__name__)

# Данные берём из Render → Environment Variables
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")

REMOTE_FILE = "/home/container/tlmodssuggestions.json"

def sftp_connect():
    client = paramiko.Transport((SFTP_HOST, 2022))
    client.connect(username=SFTP_USER, password=SFTP_PASS)
    return client

@app.route("/list", methods=["GET"])
def list_mods():
    client = sftp_connect()
    sftp = paramiko.SFTPClient.from_transport(client)

    try:
        with sftp.open(REMOTE_FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    sftp.close()
    client.close()

    return jsonify(data)

@app.route("/add", methods=["POST"])
def add_mod():
    body = request.json
    link = body.get("link")
    desc = body.get("desc", "")

    client = sftp_connect()
    sftp = paramiko.SFTPClient.from_transport(client)

    # читаем файл
    try:
        with sftp.open(REMOTE_FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    new_mod = {
        "id": len(data) + 1,
        "link": link,
        "desc": desc
    }

    data.append(new_mod)

    # записываем файл
    with sftp.open(REMOTE_FILE, "w") as f:
        f.write(json.dumps(data, indent=2))

    sftp.close()
    client.close()

    return jsonify({"status": "ok", "added": new_mod})
