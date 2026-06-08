#!/usr/bin/env python3
"""
Daily Bolao Copa 2026 email - autonomous runner.

Generates the day's email with Claude (Anthropic API), then sends it via SMTP.
Designed to run unattended in GitHub Actions on a daily cron. Standard library
only - no pip install required.

The routine spec (and any data files) committed to the repo are the single
source of truth: this script just feeds them to the model and delivers the
result. Edit the routine spec to change what the email says.

Required environment variables (set as GitHub repo secrets):
  ANTHROPIC_API_KEY  - Anthropic API key (console.anthropic.com)
  SMTP_USER          - full sending address, e.g. you@yahoo.com.br
  SMTP_PASS          - app password for that mailbox (NOT your login password)

Optional (sensible defaults shown):
  SMTP_HOST          - smtp.mail.yahoo.com
  SMTP_PORT          - 465  (SSL; use 587 for STARTTLS)
  EMAIL_TO           - tiagosa@yahoo.com.br
  EMAIL_FROM         - defaults to SMTP_USER
  ANTHROPIC_MODEL    - claude-sonnet-4-6
  ROUTINE_FILE       - bolao-copa-2026-routine.md
  DATA_DIR           - data
"""

import datetime
import json
import os
import smtplib
import ssl
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"


def env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and not val:
        sys.exit(f"ERROR: required environment variable {name} is not set.")
    return val


def load_context():
    """Concatenate the routine spec and any data files for model context."""
    parts = []
    routine_file = Path(env("ROUTINE_FILE", "bolao-copa-2026-routine.md"))
    if routine_file.exists():
        parts.append(f"# Routine spec ({routine_file.name})\n\n" + routine_file.read_text(encoding="utf-8"))
    else:
        print(f"WARNING: routine file '{routine_file}' not found.", file=sys.stderr)

    data_dir = Path(env("DATA_DIR", "data"))
    if data_dir.is_dir():
        for f in sorted(data_dir.glob("**/*")):
            if f.is_file() and f.suffix.lower() in {".md", ".txt", ".json", ".csv"}:
                parts.append(f"# Data file: {f.as_posix()}\n\n" + f.read_text(encoding="utf-8"))

    return "\n\n---\n\n".join(parts)


def generate_email(context):
    """Call the Anthropic API and return {subject, body_text, body_html}."""
    api_key = env("ANTHROPIC_API_KEY", required=True)
    model = env("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    today = datetime.date.today().isoformat()

    system = (
        "You are the automated daily assistant for a FIFA World Cup 2026 betting pool "
        "(bolao Copa 2026). Follow the routine spec provided by the user exactly. "
        "Produce the email for TODAY only. "
        "Respond with STRICT JSON and nothing else, in this exact shape: "
        '{"subject": "...", "body_text": "...", "body_html": "..."}. '
        "body_text is a plain-text version; body_html is a simple, clean HTML version. "
        "Do not include any commentary outside the JSON object."
    )
    user = (
        f"Today's date: {today}\n\n"
        f"=== CONTEXT (routine spec + data) ===\n\n{context}\n\n"
        "=== TASK ===\nGenerate today's bolao email now."
    )

    payload = {
        "model": model,
        "max_tokens": 3000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)

    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()

    # Be tolerant of accidental code fences or stray prose around the JSON.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        sys.exit(f"ERROR: model did not return JSON. Got:\n{text[:500]}")
    return json.loads(text[start:end + 1])


def send(subject, body_text, body_html=None):
    smtp_user = env("SMTP_USER", required=True)
    smtp_pass = env("SMTP_PASS", required=True)
    smtp_host = env("SMTP_HOST", "smtp.mail.yahoo.com")
    smtp_port = int(env("SMTP_PORT", "465"))
    email_to = env("EMAIL_TO", "tiagosa@yahoo.com.br")
    email_from = env("EMAIL_FROM", smtp_user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(body_text or "(no content)")
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    context = ssl.create_default_context()
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=60) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as s:
            s.starttls(context=context)
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    return email_to


def main():
    context = load_context()
    if not context.strip():
        print("WARNING: no routine/data context found; the email will be generated from defaults only.", file=sys.stderr)
    email = generate_email(context)
    recipient = send(email.get("subject", "Bolao Copa 2026"), email.get("body_text", ""), email.get("body_html"))
    print(f"Sent: {email.get('subject')!r} -> {recipient}")


if __name__ == "__main__":
    main()

