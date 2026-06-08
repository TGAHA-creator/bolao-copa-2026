#!/usr/bin/env python3
"""
Daily Bolao Copa 2026 email - autonomous runner (with live web research + persistence).

Pipeline per the routine spec (bolao-copa-2026-routine.md, the single source of truth):
  STEP 1 GRADE  - read prior predictions + log.md, web-search real results, grade.
  STEP 2 SCOPE  - web-search the WC2026 schedule; matches in the next 24-36h (Asia/Dubai).
  STEP 3 PREDICT- web-search rankings/Elo/form/injuries/odds; EV-optimal picks.
  STEP 4 LOG    - write predictions/<date>.json and the updated log.md (committed by the workflow).
  STEP 5 EMAIL  - send the pt-BR email via SMTP.

The model is given the Anthropic web_search server tool so STEPS 1-3 use live data.
Standard library only - no pip install required.

Env (mapped from repo secrets in the workflow):
  ANTHROPIC_API_KEY   - Anthropic API key
  SMTP_USER           - full sending address (Gmail)
  SMTP_PASS           - Gmail app password (NOT the login password)
Optional (defaults shown):
  SMTP_HOST=smtp.gmail.com  SMTP_PORT=465  EMAIL_TO=tiagogsa@yahoo.com.br
  EMAIL_FROM=<SMTP_USER>     ANTHROPIC_MODEL=claude-sonnet-4-5
  ROUTINE_FILE=bolao-copa-2026-routine.md   DATA_DIR=data
  PREDICTIONS_DIR=predictions               LOG_FILE=log.md
  WEB_SEARCH_MAX_USES=15
"""

import datetime
import json
import os
import smtplib
import ssl
import sys
import urllib.request
import urllib.error
from email.message import EmailMessage
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"


def env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and not val:
        sys.exit(f"ERROR: required environment variable {name} is not set.")
    return val


def load_context():
    """Routine spec + data files + existing log.md + all prior predictions (for grading)."""
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

    log_file = Path(env("LOG_FILE", "log.md"))
    if log_file.exists():
        parts.append(f"# Current {log_file.name} (history + LESSONS)\n\n" + log_file.read_text(encoding="utf-8"))
    else:
        parts.append(f"# Current {log_file.name}\n\n(empty - no history yet; nothing to grade on the first run)")

    pred_dir = Path(env("PREDICTIONS_DIR", "predictions"))
    if pred_dir.is_dir():
        preds = sorted(pred_dir.glob("*.json"))
        if preds:
            blob = []
            for f in preds:
                blob.append(f"## {f.name}\n```json\n{f.read_text(encoding='utf-8')}\n```")
            parts.append("# Prior predictions (grade any whose matches have been played and are not yet in log.md)\n\n"
                         + "\n\n".join(blob))

    return "\n\n---\n\n".join(parts)


def call_model(context):
    raw_key = env("ANTHROPIC_API_KEY", required=True)
    api_key = raw_key.strip()  # tolerate stray whitespace/newline from a pasted secret
    model = env("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    max_uses = int(env("WEB_SEARCH_MAX_USES", "15"))
    today = datetime.date.today().isoformat()

    system = (
        "You are the automated daily assistant for the FIFA World Cup 2026 betting pool "
        "(\"Bolao Copa 2026\"). The routine spec in the user message is the single source of "
        "truth - follow it EXACTLY: the scoring system, the EV-optimal pick logic, the per-match "
        "card format, and the rule that the email is written ENTIRELY in Brazilian Portuguese. "
        "Use the web_search tool for live data: (1) grade any prior predictions whose matches were "
        "already played by searching the real final scores; (2) find every match kicking off in the "
        "next 24-36h and convert kickoffs to Asia/Dubai (GST, UTC+4); (3) research rankings/Elo, "
        "recent form, injuries/suspensions, venue/altitude/heat/rest, and current bookmaker + "
        "Polymarket prices, de-vigged into consensus probabilities. If there are no matches in the "
        "window, the email body is the single line 'Nenhum jogo na janela'. State any assumption you "
        "must make; never invent rule details.\n\n"
        "Respond with STRICT JSON ONLY (no prose, no code fences), exactly this shape:\n"
        "{\n"
        '  "subject": "Bolao Copa 2026 - palpites para <data> (<n> jogos)",\n'
        '  "body_text": "plain-text pt-BR email",\n'
        '  "body_html": "clean simple HTML pt-BR email",\n'
        '  "had_matches": true,\n'
        '  "predictions": [\n'
        '    {"match":"TIME A vs TIME B","kickoff_gst":"YYYY-MM-DD HH:MM","venue":"...",\n'
        '     "outcome":"A|Empate|B","score":"X-Y",\n'
        '     "p_model":{"A":0.0,"draw":0.0,"B":0.0},\n'
        '     "p_consensus":{"A":0.0,"draw":0.0,"B":0.0},\n'
        '     "xg":{"A":0.0,"B":0.0},"base_pts":0,"est_total_pts":0,\n'
        '     "edge":"...","notes":"..."}\n'
        "  ],\n"
        '  "log_md": "the FULL updated contents of log.md: a LESSONS list (max 10 bullets) at the '
        "top, then the running graded history with today's newly graded matches appended. Preserve "
        'all prior entries."\n'
        "}\n"
        "If had_matches is false, predictions is [] but still return log_md (updated if you graded "
        "anything, otherwise unchanged)."
    )
    user = (
        f"Today's date: {today} (treat kickoff times in Asia/Dubai, UTC+4).\n\n"
        f"=== CONTEXT (routine spec + data + log + prior predictions) ===\n\n{context}\n\n"
        "=== TASK ===\nDo STEP 1 (grade) through STEP 5 (compose email) now, then return the JSON."
    )

    payload = {
        "model": model,
        "max_tokens": 16000,
        "system": system,
        "tools": [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
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
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 401:
            if api_key.startswith("sk-ant-api"):
                cls = "standard-api-key(sk-ant-api...)"
            elif api_key.startswith("sk-ant-oat"):
                cls = "oauth-token(sk-ant-oat...) -- needs Authorization: Bearer, NOT x-api-key"
            elif not api_key:
                cls = "EMPTY"
            else:
                cls = "unrecognized-prefix(not sk-ant-...)"
            print(f"DIAG 401: key_len={len(api_key)} class={cls} "
                  f"had_surrounding_whitespace={raw_key != api_key}", file=sys.stderr)
        sys.exit(f"ERROR: Anthropic API HTTP {e.code}: {body[:1000]}")

    # Concatenate all final text blocks (web_search_tool_result / server_tool_use blocks are skipped).
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    if not text:
        sys.exit(f"ERROR: model returned no text. stop_reason={data.get('stop_reason')} raw={json.dumps(data)[:800]}")

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        sys.exit(f"ERROR: model did not return JSON. Got:\n{text[:800]}")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: could not parse model JSON: {e}\n---\n{text[start:end + 1][:1200]}")


def persist(result):
    """Write predictions/<date>.json and log.md. Returns list of paths written."""
    written = []
    today = datetime.date.today().isoformat()

    preds = result.get("predictions") or []
    if preds:
        pred_dir = Path(env("PREDICTIONS_DIR", "predictions"))
        pred_dir.mkdir(parents=True, exist_ok=True)
        p = pred_dir / f"{today}.json"
        p.write_text(json.dumps(preds, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(p))

    log_md = result.get("log_md")
    if log_md and log_md.strip():
        lf = Path(env("LOG_FILE", "log.md"))
        lf.write_text(log_md.rstrip() + "\n", encoding="utf-8")
        written.append(str(lf))

    return written


def send(subject, body_text, body_html=None):
    smtp_user = env("SMTP_USER", required=True)
    smtp_pass = env("SMTP_PASS", required=True)
    smtp_host = env("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(env("SMTP_PORT", "465"))
    email_to = env("EMAIL_TO", "tiagogsa@yahoo.com.br")
    email_from = env("EMAIL_FROM", smtp_user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(body_text or "(sem conteudo)")
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    ctx = ssl.create_default_context()
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=60) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as s:
            s.starttls(context=ctx)
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    return email_to


def main():
    context = load_context()
    if not context.strip():
        print("WARNING: no routine/data context found.", file=sys.stderr)

    result = call_model(context)

    written = persist(result)
    if written:
        print("Wrote: " + ", ".join(written))
    else:
        print("No prediction/log files to write this run.")

    recipient = send(
        result.get("subject", "Bolao Copa 2026"),
        result.get("body_text", ""),
        result.get("body_html"),
    )
    print(f"Sent: {result.get('subject')!r} -> {recipient} "
          f"(matches={len(result.get('predictions') or [])})")


if __name__ == "__main__":
    main()
