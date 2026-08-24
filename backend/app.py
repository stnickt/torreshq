import hmac
import html
import os
import re
import secrets
import smtplib
import sqlite3
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, jsonify, request

from rcon import rcon_command

app = Flask(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
TO_EMAIL = os.environ.get("TO_EMAIL", SMTP_USER)

DB_PATH = os.environ.get("DB_PATH", "/app/data/requests.db")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://torreshq.com").rstrip("/")

RCON_HOST = os.environ.get("RCON_HOST")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ.get("RCON_PASSWORD")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Allows an optional leading "." — Floodgate prefixes Bedrock players' names
# with one, e.g. Java "stnickt" vs Bedrock ".stnickt".
MC_USERNAME_RE = re.compile(r"^\.?[A-Za-z0-9_]{3,16}$")


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
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                token TEXT NOT NULL DEFAULT ''
            )
            """
        )
        # Migrate databases created before status/token existed.
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(requests)")}
        if "status" not in existing_columns:
            conn.execute("ALTER TABLE requests ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        if "token" not in existing_columns:
            conn.execute("ALTER TABLE requests ADD COLUMN token TEXT NOT NULL DEFAULT ''")


def save_request(name, email, minecraft_username):
    token = secrets.token_urlsafe(24)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO requests (name, email, minecraft_username, created_at, status, token)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (name, email, minecraft_username, datetime.now(timezone.utc).isoformat(), token),
        )
        return cursor.lastrowid, token


def get_request(request_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()


def set_status(request_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))


def page(title, body):
    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        f"<style>body{{font-family:-apple-system,sans-serif;max-width:480px;margin:3rem auto;"
        f"padding:0 1.5rem;line-height:1.6}}"
        f"button{{font:inherit;padding:.6rem 1.2rem;border-radius:8px;border:none;"
        f"background:#4f46e5;color:#fff;cursor:pointer}}</style></head>"
        f"<body><h1>{html.escape(title)}</h1>{body}</body></html>"
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

    if not MC_USERNAME_RE.match(minecraft_username):
        return jsonify(ok=False, error="That doesn't look like a valid Minecraft username."), 400

    request_id, token = save_request(name, email, minecraft_username)

    accept_url = f"{PUBLIC_BASE_URL}/api/request-access/{request_id}/review?token={token}&action=accept"
    deny_url = f"{PUBLIC_BASE_URL}/api/request-access/{request_id}/review?token={token}&action=deny"

    message = EmailMessage()
    message["Subject"] = "Minecraft access request"
    message["From"] = SMTP_USER
    message["To"] = TO_EMAIL
    message["Reply-To"] = email
    message.set_content(
        f"Name: {name}\nEmail: {email}\nMinecraft username: {minecraft_username}\n\n"
        f"Accept: {accept_url}\nDeny: {deny_url}\n"
    )
    message.add_alternative(
        f"""
        <div style="font-family:-apple-system,sans-serif">
          <p><b>Name:</b> {html.escape(name)}<br>
             <b>Email:</b> {html.escape(email)}<br>
             <b>Minecraft username:</b> {html.escape(minecraft_username)}</p>
          <p>
            <a href="{accept_url}" style="background:#0b8043;color:#fff;padding:.6rem 1.2rem;
               border-radius:8px;text-decoration:none;margin-right:.5rem">Accept</a>
            <a href="{deny_url}" style="background:#b3261e;color:#fff;padding:.6rem 1.2rem;
               border-radius:8px;text-decoration:none">Deny</a>
          </p>
        </div>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)
    except smtplib.SMTPException:
        # Not a 5xx: Cloudflare replaces 502/504-class origin responses with
        # its own generic error page, hiding this message from the client.
        return jsonify(ok=False, error="Failed to send email.")

    return jsonify(ok=True)


@app.get("/api/request-access/<int:request_id>/review")
def review_request(request_id):
    token = request.args.get("token", "")
    action = request.args.get("action", "")

    row = get_request(request_id)
    if row is None or not hmac.compare_digest(row["token"], token):
        return page("Not found", "<p>This link is invalid.</p>"), 404

    if action not in ("accept", "deny"):
        return page("Invalid link", "<p>Unrecognized action.</p>"), 400

    if row["status"] != "pending":
        return page(
            "Already handled",
            f"<p>This request was already <b>{html.escape(row['status'])}</b>.</p>",
        )

    verb = "Accept" if action == "accept" else "Deny"
    return page(
        f"{verb} access request?",
        f"""
        <p><b>Name:</b> {html.escape(row['name'])}<br>
           <b>Email:</b> {html.escape(row['email'])}<br>
           <b>Minecraft username:</b> {html.escape(row['minecraft_username'])}</p>
        <form method="POST" action="/api/request-access/{request_id}/confirm">
          <input type="hidden" name="token" value="{html.escape(token)}">
          <input type="hidden" name="action" value="{html.escape(action)}">
          <button type="submit">Confirm {verb}</button>
        </form>
        """,
    )


@app.post("/api/request-access/<int:request_id>/confirm")
def confirm_request(request_id):
    token = request.form.get("token", "")
    action = request.form.get("action", "")

    row = get_request(request_id)
    if row is None or not hmac.compare_digest(row["token"], token):
        return page("Not found", "<p>This link is invalid.</p>"), 404

    if action not in ("accept", "deny"):
        return page("Invalid link", "<p>Unrecognized action.</p>"), 400

    if row["status"] != "pending":
        return page(
            "Already handled",
            f"<p>This request was already <b>{html.escape(row['status'])}</b>.</p>",
        )

    if action == "deny":
        set_status(request_id, "denied")
        return page("Denied", f"<p>Denied access for <b>{html.escape(row['minecraft_username'])}</b>.</p>")

    username = row["minecraft_username"]
    if not MC_USERNAME_RE.match(username):
        set_status(request_id, "accept_failed")
        return page("Error", "<p>Stored username looks invalid — whitelist it manually.</p>"), 400

    if not RCON_HOST or not RCON_PASSWORD:
        set_status(request_id, "accept_failed")
        return page(
            "RCON not configured",
            f"<p>Accepted, but RCON_HOST/RCON_PASSWORD aren't set — "
            f"whitelist <b>{html.escape(username)}</b> manually.</p>",
        )

    # We don't know if this is a Java or Bedrock (Floodgate-prefixed) player,
    # so whitelist both forms of the name to cover either case.
    base_username = username[1:] if username.startswith(".") else username
    variants = [base_username, f".{base_username}"]

    succeeded = []
    failed = []
    for variant in variants:
        try:
            result = rcon_command(RCON_HOST, RCON_PORT, RCON_PASSWORD, f"whitelist add {variant}")
            succeeded.append((variant, result))
        except Exception as exc:
            failed.append((variant, str(exc)))

    if not succeeded:
        set_status(request_id, "accept_failed")
        # Not a 5xx: Cloudflare replaces 502/504-class origin responses with
        # its own generic error page, hiding this message from the browser.
        return page(
            "Whitelist failed",
            f"<p>Could not reach the Minecraft server: {html.escape(failed[0][1])}<br>"
            f"Whitelist <b>{html.escape(base_username)}</b> (and <b>.{html.escape(base_username)}</b>"
            f" if they're on Bedrock) manually.</p>",
        )

    set_status(request_id, "accepted")
    items = "".join(f"<li><b>{html.escape(v)}</b>: {html.escape(r)}</li>" for v, r in succeeded)
    note = (
        f"<p>Note: also tried <b>{html.escape(failed[0][0])}</b> but that failed — that's expected "
        f"if it's not the edition they play on.</p>"
        if failed
        else ""
    )
    return page("Accepted", f"<p>Whitelisted both forms, covering Java and Bedrock:</p><ul>{items}</ul>{note}")
