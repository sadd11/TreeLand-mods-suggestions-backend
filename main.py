from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import paramiko

app = Flask(__name__)
CORS(app)

# ==========================
#   НАСТРОЙКИ
# ==========================

ADMIN_PASSWORD = "tl-358856"

SFTP_HOST = "generation.bkn.s-hub.xyz"   # ← ТВОЙ ХОСТ
SFTP_PORT = 2022
SFTP_USER = "weeewerwy.44b9896b"         # ← ТВОЙ ЛОГИН
SFTP_PASS = "55555Mir42spider99lol"        # ← ВСТАВЬ ПАРОЛЬ

REMOTE_FILE = "tlmodssuggestions.json"    # ФАЙЛ НА СЕРВЕРЕ


# ==========================
#   SFTP ФУНКЦИИ
# ==========================

def sftp_connect():
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    return transport


def load_mods():
    try:
        client = sftp_connect()
        sftp = paramiko.SFTPClient.from_transport(client)

        try:
            with sftp.open(REMOTE_FILE, "r") as f:
                data = f.read().decode("utf-8")
                mods = json.loads(data)
        except IOError:
            mods = []

        sftp.close()
        client.close()
        return mods

    except Exception as e:
        print("Ошибка чтения:", e)
        return []


def save_mods(mods):
    try:
        client = sftp_connect()
        sftp = paramiko.SFTPClient.from_transport(client)

        with sftp.open(REMOTE_FILE, "w") as f:
            f.write(json.dumps(mods, ensure_ascii=False, indent=2))

        sftp.close()
        client.close()
        return True

    except Exception as e:
        print("Ошибка записи:", e)
        return False


# ==========================
#   API: ДОБАВИТЬ МОД
# ==========================

@app.route("/add", methods=["POST"])
def add_mod():
    data = request.json

    url = data.get("url")
    reason = data.get("reason")
    nick = data.get("nick")

    if not url or not reason:
        return jsonify({"error": "missing fields"}), 400

    mods = load_mods()

    new_id = max([m["id"] for m in mods], default=0) + 1

    new_mod = {
        "id": new_id,
        "url": url,
        "reason": reason,
        "nick": nick,
        "createdAt": datetime.utcnow().isoformat(),
        "status": "pending"
    }

    mods.append(new_mod)
    save_mods(mods)

    return jsonify({"ok": True, "id": new_id})


# ==========================
#   API: СПИСОК ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ==========================

@app.route("/list", methods=["GET"])
def list_mods():
    mods = load_mods()
    # пользователи видят только approved + pending
    visible = [m for m in mods if m["status"] in ("approved", "pending")]
    return jsonify(visible)


# ==========================
#   API: СПИСОК ДЛЯ АДМИНКИ
# ==========================

@app.route("/admin/list-all", methods=["GET"])
def admin_list_all():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 403

    return jsonify(load_mods())


# ==========================
#   API: ОДОБРИТЬ МОД
# ==========================

@app.route("/admin/approve", methods=["POST"])
def admin_approve():
    data = request.json
    mod_id = data.get("id")
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 403

    mods = load_mods()
    for mod in mods:
        if mod["id"] == mod_id:
            mod["status"] = "approved"
            break

    save_mods(mods)
    return jsonify({"ok": True})


# ==========================
#   API: ОТКЛОНИТЬ МОД
# ==========================

@app.route("/admin/reject", methods=["POST"])
def admin_reject():
    data = request.json
    mod_id = data.get("id")
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 403

    mods = load_mods()
    for mod in mods:
        if mod["id"] == mod_id:
            mod["status"] = "rejected"
            break

    save_mods(mods)
    return jsonify({"ok": True})


# ==========================
#   API: УДАЛИТЬ МОД
# ==========================

@app.route("/admin/delete", methods=["POST"])
def admin_delete():
    data = request.json
    mod_id = data.get("id")
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 403

    mods = load_mods()
    mods = [m for m in mods if m["id"] != mod_id]

    save_mods(mods)
    return jsonify({"ok": True})


# ==========================
#   START
# ==========================

@app.route("/", methods=["GET"])
def home():
    return "Treeland Suggestions Backend is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
