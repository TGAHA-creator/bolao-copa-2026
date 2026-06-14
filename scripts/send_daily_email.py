#!/usr/bin/env python3
"""
Daily Bolao Copa 2026 email - autonomous runner (with live web research + persistence).

Pipeline per the routine spec (bolao-copa-2026-routine.md, the single source of truth):
  STEP 1 GRADE  - read prior predictions + log.md, web-search real results, grade.
  STEP 2 SCOPE  - web-search the WC2026 schedule; matches in the next 24-36h (Asia/Dubai).
  STEP 3 PREDICT- web-search rankings/Elo/form/injuries/odds; EV-optimal picks.
  STEP 4 LOG    - write predictions/<date>.json and the updated log.md (committed by the workflow).
  STEP 5 EMAIL  - send the pt-BR email via SMTP.
  STEP 6 INGEST - POST the analysis (dashboard contract) to the Bolao Dashboard (this fork).

The model is given the Anthropic web_search server tool so STEPS 1-3 use live data.
Standard library only - no pip install required.

Env (mapped from repo secrets in the workflow):
  ANTHROPIC_API_KEY   - Anthropic API key
  SMTP_USER           - full sending address (Gmail)
  SMTP_PASS           - Gmail app password (NOT the login password)
Optional (defaults shown):
  SMTP_HOST=smtp.gmail.com  SMTP_PORT=465  EMAIL_TO=tiagogsa@yahoo.com.br
  EMAIL_FROM=<SMTP_USER>     ANTHROPIC_MODEL=claude-sonnet-4-6
  ROUTINE_FILE=bolao-copa-2026-routine.md   DATA_DIR=data
  PREDICTIONS_DIR=predictions               LOG_FILE=log.md
  WEB_SEARCH_MAX_USES=15
Dashboard ingest (optional - skipped if unset):
  INGEST_URL          - e.g. https://your-app.vercel.app/api/ingest
  INGEST_SECRET       - the dashboard's INGEST_SECRET (sent as Authorization: Bearer)
"""

import datetime
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.request
import urllib.error
from email.message import EmailMessage
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"

# Asia/Dubai (GST) is UTC+4 with no DST.
GST = datetime.timezone(datetime.timedelta(hours=4))

# Confidence thresholds applied to the picked outcome's (de-vigged) probability.
CONF_HIGH = 0.55
CONF_MEDIUM = 0.40


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
    model = env("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    max_uses = int(env("WEB_SEARCH_MAX_USES", "15"))
    today = datetime.date.today().isoformat()
    # Default scope = tomorrow's matches in Asia/Dubai (predict the day before kickoff, exactly once).
    # WINDOW_HOURS is an optional preview override (manual dispatch) that switches to an N-hour window.
    window_hours = env("WINDOW_HOURS", "").strip()
    gst_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)
    tomorrow_gst = (gst_now.date() + datetime.timedelta(days=1)).isoformat()
    if window_hours and window_hours != "0":
        scope_instr = (
            f"SCOPE for STEP 2 (preview override): include every FIFA World Cup 2026 match kicking off within "
            f"the next {window_hours} hours from now (Asia/Dubai). Produce full STEP 3 predictions for all of "
            f"them; do not return an empty 'no games' email if matches fall in this window."
        )
    else:
        scope_instr = (
            f"SCOPE for STEP 2: predict EVERY FIFA World Cup 2026 match whose kickoff falls on the Asia/Dubai "
            f"calendar day {tomorrow_gst} (that is tomorrow). Do NOT predict matches on any other day. If there "
            f"are no matches on {tomorrow_gst}, return the single-line 'Nenhum jogo na janela' email and write "
            f"no predictions file."
        )

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
        '  "matchday": "stage label, e.g. \\"Group Stage - Matchday 2\\" or \\"Round of 16\\"",\n'
        '  "summary": "one or two sentence pt-BR overview of the day",\n'
        '  "predictions": [\n'
        '    {"match":"TIME A vs TIME B","competition":"ex.: Grupo G ou Oitavas",\n'
        '     "kickoff_gst":"YYYY-MM-DD HH:MM","venue":"...",\n'
        '     "outcome":"A|Empate|B","score":"X-Y",\n'
        '     "p_model":{"A":0.0,"draw":0.0,"B":0.0},\n'
        '     "p_consensus":{"A":0.0,"draw":0.0,"B":0.0},\n'
        '     "xg":{"A":0.0,"B":0.0},"base_pts":0,"est_total_pts":0,\n'
        '     "alt_scores":[{"score":"X-Y","prob":0.0}],\n'
        '     "key_factors":["fator 1","fator 2","fator 3"],\n'
        '     "edge":"...","reading":"...","notes":"..."}\n'
        "  ],\n"
        '  "research": [{"title":"short label","notes":"1-2 sentence research note"}],\n'
        '  "grading": {"date":"YYYY-MM-DD","results":[{"match":"...","predicted":"X-Y",'
        '"actual":"X-Y","pointsEarned":0,"note":"..."}],"totalPoints":0,"lessons":"..."},\n'
        '  "standings": {"totalSeasonPoints":0,"rank":"—"},\n'
        '  "log_md": "the FULL updated contents of log.md: a LESSONS list (max 10 bullets) at the '
        "top, then the running graded history with today's newly graded matches appended. Preserve "
        'all prior entries."\n'
        "}\n"
        "The matchday, summary, per-match competition, research, grading and standings fields power a "
        "web dashboard, so keep them consistent with the email: 'grading' mirrors the matches you "
        "graded in STEP 1 (use null if you graded nothing); 'standings.totalSeasonPoints' is the running "
        "cumulative points AFTER applying today's grading. "
        "All probabilities (p_model, p_consensus, alt_scores.prob) are fractions in [0,1]; each p_model "
        "and p_consensus triple sums to ~1.0. alt_scores lists 2-3 other likely scorelines with their "
        "probability; key_factors is 3-4 short Brazilian-Portuguese factors; reading and edge are in "
        "Brazilian Portuguese. These per-match fields (model vs market, xg, alt_scores, key_factors, "
        "reading, edge) power the web dashboard cards, so fill them for every match. "
        "If had_matches is false, predictions is [] but still return log_md, grading and standings "
        "(updated if you graded anything, otherwise unchanged)."
    )
    user = (
        f"Today's date: {today} (treat kickoff times in Asia/Dubai, UTC+4).\n\n"
        f"{scope_instr}\n\n"
        f"=== CONTEXT (routine spec + data + log + prior predictions) ===\n\n{context}\n\n"
        "=== TASK ===\nDo STEP 1 (grade) through STEP 5 (compose email) now, then return the JSON."
    )

    payload = {
        "model": model,
        "max_tokens": 32000,
        "system": system,
        "tools": [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
        "messages": [{"role": "user", "content": user}],
        "stream": True,  # stream so long web-search runs don't drop the connection (RemoteDisconnected)
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    def stream_once():
        """One streamed attempt; returns the concatenated text-delta output."""
        req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        parts = []
        with urllib.request.urlopen(req, timeout=300) as resp:  # 300s = per-read idle cap; stream stays warm
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    ev = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                et = ev.get("type")
                if et == "content_block_delta" and ev.get("delta", {}).get("type") == "text_delta":
                    parts.append(ev["delta"].get("text", ""))
                elif et == "error":
                    raise RuntimeError(f"stream error: {ev.get('error')}")
        return "".join(parts).strip()

    text, last_err = "", None
    for attempt in range(3):
        try:
            text = stream_once()
            if text:
                break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 529):  # transient: rate limit / overload — retry
                retry_after = e.headers.get("retry-after")
                delay = int(retry_after) if (retry_after and retry_after.isdigit()) else 20 * (attempt + 1)
                last_err = f"HTTP {e.code}: {body[:200]}"
                print(f"WARN: model call attempt {attempt + 1}/3 got HTTP {e.code}; "
                      f"retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                continue
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
            sys.exit(f"ERROR: Anthropic API HTTP {e.code}: {body[:1000]}")  # other 4xx: don't retry
        except (urllib.error.URLError, OSError, RuntimeError) as e:
            last_err = e
            print(f"WARN: model call attempt {attempt + 1}/3 failed "
                  f"({type(e).__name__}: {e}); retrying...", file=sys.stderr)
            time.sleep(5 * (attempt + 1))

    if not text:
        sys.exit(f"ERROR: model returned no text after retries. last_err={last_err}")

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


# --------------------------- dashboard ingest ----------------------------

def gst_to_utc_iso(kickoff_gst):
    """'YYYY-MM-DD HH:MM' (Asia/Dubai) -> '...T..:..:00Z' (UTC). None on failure."""
    if not kickoff_gst:
        return None
    s = str(kickoff_gst).strip().replace("T", " ")
    try:
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=GST)
    except ValueError:
        return None
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _confidence(pred):
    """High/Medium/Low from the strongest (de-vigged) outcome probability."""
    probs = pred.get("p_consensus") or pred.get("p_model") or {}
    vals = [v for v in probs.values() if isinstance(v, (int, float))]
    pmax = max(vals) if vals else 0.0
    if pmax >= CONF_HIGH:
        return "High"
    if pmax >= CONF_MEDIUM:
        return "Medium"
    return "Low"


def _rationale(pred):
    edge = (pred.get("edge") or "").strip()
    notes = (pred.get("notes") or "").strip()
    if edge and notes:
        return f"{edge} — {notes}"
    return edge or notes


def _int(value, default=0):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _triple(d):
    """Map a model {A,draw,B} probability triple to {home,draw,away}."""
    if not isinstance(d, dict):
        return None
    return {
        "home": _float(d.get("A", d.get("home"))),
        "draw": _float(d.get("draw", d.get("Empate"))),
        "away": _float(d.get("B", d.get("away"))),
    }


def _outcome(value):
    """Model 'A|Empate|B' -> contract 'home|draw|away'."""
    return {
        "A": "home", "B": "away",
        "Empate": "draw", "empate": "draw", "Draw": "draw", "draw": "draw",
    }.get(str(value or "").strip())


def build_analysis(result, today):
    """Map the model's strict-JSON output to the dashboard /api/ingest contract."""
    out_preds = []
    for p in (result.get("predictions") or []):
        ep = p.get("est_total_pts")
        pred = {
            "match": p.get("match", ""),
            "competition": (p.get("competition") or "Fase de Grupos"),
            "kickoff": gst_to_utc_iso(p.get("kickoff_gst")) or "",
            "venue": p.get("venue", ""),
            "predictedScore": p.get("score", ""),
            "confidence": _confidence(p),
            "bolaoPoints": (f"~{_int(ep)}" if ep is not None else ""),
            "rationale": _rationale(p),
            "edge": p.get("edge", ""),
            "reading": p.get("reading", ""),
            "keyFactors": [
                f for f in (p.get("key_factors") or [])
                if isinstance(f, str) and f.strip()
            ],
        }
        outcome = _outcome(p.get("outcome"))
        if outcome:
            pred["outcome"] = outcome
        if p.get("base_pts") is not None:
            pred["basePoints"] = _int(p.get("base_pts"))
        if ep is not None:
            pred["estPoints"] = _float(ep)
        pm = _triple(p.get("p_model"))
        if pm:
            pred["pModel"] = pm
        pc = _triple(p.get("p_consensus"))
        if pc:
            pred["pConsensus"] = pc
        xg = p.get("xg")
        if isinstance(xg, dict):
            pred["xg"] = {
                "home": _float(xg.get("A", xg.get("home"))),
                "away": _float(xg.get("B", xg.get("away"))),
            }
        alts = [
            {"score": str(a.get("score")), "prob": _float(a.get("prob"))}
            for a in (p.get("alt_scores") or [])
            if isinstance(a, dict) and a.get("score")
        ]
        if alts:
            pred["altScores"] = alts
        out_preds.append(pred)

    # Date the analysis to the actual match day (earliest kickoff), not the run date.
    kickoffs = [pr["kickoff"] for pr in out_preds if pr.get("kickoff")]
    match_date = min(kickoffs)[:10] if kickoffs else today

    grading = result.get("grading")
    if isinstance(grading, dict) and grading:
        grading = {
            "date": grading.get("date", ""),
            "results": [
                {
                    "match": r.get("match", ""),
                    "predicted": r.get("predicted", ""),
                    "actual": r.get("actual", ""),
                    "pointsEarned": _int(r.get("pointsEarned")),
                    "note": r.get("note", ""),
                }
                for r in (grading.get("results") or [])
            ],
            "totalPoints": _int(grading.get("totalPoints")),
            "lessons": grading.get("lessons", ""),
        }
    else:
        grading = None

    standings = result.get("standings") or {}

    return {
        "date": match_date,
        "matchday": result.get("matchday", ""),
        "summary": result.get("summary", ""),
        "predictions": out_preds,
        "research": [
            {"title": r.get("title", ""), "notes": r.get("notes", "")}
            for r in (result.get("research") or [])
            if r.get("title")
        ],
        "grading": grading,
        "standings": {
            "totalSeasonPoints": _int(standings.get("totalSeasonPoints")),
            "rank": str(standings.get("rank", "—") or "—"),
        },
    }


def post_to_dashboard(payload):
    """POST the analysis to the dashboard. Non-fatal: warns and returns on failure."""
    url = (env("INGEST_URL", "") or "").strip()
    secret = (env("INGEST_SECRET", "") or "").strip()
    if not url or not secret:
        print("INGEST_URL/INGEST_SECRET not set — skipping dashboard POST.", file=sys.stderr)
        return

    data = json.dumps(payload).encode("utf-8")
    headers = {"content-type": "application/json", "authorization": f"Bearer {secret}"}

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", "replace")
                print(f"Dashboard ingest OK: HTTP {resp.status} {body[:200]}")
                return
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"WARN: dashboard ingest failed HTTP {e.code}: {body[:300]}", file=sys.stderr)
            return
        except (urllib.error.URLError, OSError) as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"WARN: dashboard ingest error: {type(e).__name__}: {e}", file=sys.stderr)
            return


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

    # POST to the dashboard before the email so a slow/broken email never blocks
    # ingest — and so a broken ingest never blocks the email (both are non-fatal).
    try:
        analysis = build_analysis(result, datetime.date.today().isoformat())
        post_to_dashboard(analysis)
    except Exception as e:  # never let dashboard issues abort the run
        print(f"WARN: could not build/post dashboard payload: {type(e).__name__}: {e}", file=sys.stderr)

    recipient = send(
        result.get("subject", "Bolao Copa 2026"),
        result.get("body_text", ""),
        result.get("body_html"),
    )
    print(f"Sent: {result.get('subject')!r} -> {recipient} "
          f"(matches={len(result.get('predictions') or [])})")


if __name__ == "__main__":
    main()
