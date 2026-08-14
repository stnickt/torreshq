import os
import re
import smtplib
import sqlite3
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
TO_EMAIL = os.environ.get("TO_EMAIL", SMTP_USER)

DB_PATH = os.environ.get("DB_PATH", "/app/data/requests.db")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                minecraft_username TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_request(name, email, minecraft_username):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO requests (name, email, minecraft_username, created_at) VALUES (?, ?, ?, ?)",
            (name, email, minecraft_username, datetime.now(timezone.utc).isoformat()),
        )


init_db()


@app.post("/api/request-access")
def request_access():
    data = request.get_json(silent=True) or {}

    if data.get("_honey"):
        return jsonify(ok=True)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    minecraft_username = (data.get("minecraft_username") or "").strip()

    if not name or not email or not minecraft_username or not EMAIL_RE.match(email):
        return jsonify(ok=False, error="Please fill out all fields with a valid email."), 400

    save_request(name, email, minecraft_username)

    message = EmailMessage()
    message["Subject"] = "Minecraft access request"
    message["From"] = SMTP_USER
    message["To"] = TO_EMAIL
    message["Reply-To"] = email
    message.set_content(
        f"Name: {name}\nEmail: {email}\nMinecraft username: {minecraft_username}\n"
    )

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)
    except smtplib.SMTPException:
        return jsonify(ok=False, error="Failed to send email."), 502

    return jsonify(ok=True)
