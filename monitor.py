#!/usr/bin/env python3
"""
webpage-monitor
---------------
Check a URL once, compare it to what it looked like last time, and email you
only when it changed (or every run, if you prefer).

Everything specific to *your* use is supplied through environment variables, so
this file contains no URLs, emails, or secrets and is safe to commit publicly.

Extraction modes (set MONITOR_MODE):
  raw       hash the entire response body (default)
  json      pull one field out of a JSON response, via MONITOR_FIELD (dot path,
            e.g. "footerMessage" or "data.items.0.title")
  selector  pull text from an HTML element, via MONITOR_SELECTOR (a CSS selector,
            e.g. "#notice" or ".alert-banner"); requires beautifulsoup4

See README.md for full setup.
"""

import hashlib
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from urllib.request import Request, urlopen


def env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and (val is None or val == ""):
        sys.exit(f"ERROR: required environment variable {name} is not set.")
    return val


def fetch(url, headers):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def dig(obj, dotted_path):
    """Walk a dotted path into nested dicts/lists. '0' indexes into a list."""
    cur = obj
    for part in dotted_path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def extract(body, mode, field, selector):
    if mode == "raw":
        return body
    if mode == "json":
        if not field:
            sys.exit("ERROR: MONITOR_MODE=json requires MONITOR_FIELD.")
        return str(dig(json.loads(body), field))
    if mode == "selector":
        if not selector:
            sys.exit("ERROR: MONITOR_MODE=selector requires MONITOR_SELECTOR.")
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            sys.exit("ERROR: selector mode needs beautifulsoup4 (pip install beautifulsoup4).")
        el = BeautifulSoup(body, "html.parser").select_one(selector)
        if el is None:
            sys.exit(f"ERROR: selector '{selector}' matched nothing on the page.")
        return el.get_text("\n", strip=True)
    sys.exit(f"ERROR: unknown MONITOR_MODE '{mode}'.")


def send_email(subject, body):
    host = env("SMTP_HOST", required=True)
    port = int(env("SMTP_PORT", "587"))
    user = env("SMTP_USER", required=True)
    password = env("SMTP_PASS", required=True)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = env("EMAIL_FROM", user)
    msg["To"] = env("EMAIL_TO", required=True)
    msg.set_content(body)
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)


def main():
    url = env("MONITOR_URL", required=True)
    mode = env("MONITOR_MODE", "raw")
    field = env("MONITOR_FIELD")
    selector = env("MONITOR_SELECTOR")
    label = env("MONITOR_LABEL", url)  # human-friendly name used in subjects
    state_file = env("STATE_FILE", "state.json")
    always_email = env("ALWAYS_EMAIL", "false").lower() in ("1", "true", "yes")

    headers = {}
    raw_headers = env("MONITOR_HEADERS")  # optional JSON object of extra headers
    if raw_headers:
        headers.update(json.loads(raw_headers))
    headers.setdefault("User-Agent", "webpage-monitor/1.0")

    content = extract(fetch(url, headers), mode, field, selector)
    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    prior = {}
    if os.path.exists(state_file):
        with open(state_file) as f:
            prior = json.load(f)
    old_hash = prior.get("hash")

    changed = old_hash is not None and new_hash != old_hash
    first_run = old_hash is None

    if changed:
        send_email(f"CHANGED — {label}",
                   f"The monitored content changed.\n\nNew content:\n\n{content}")
        print("CHANGE DETECTED — email sent.")
    elif first_run:
        send_email(f"Monitoring started — {label}",
                   f"Baseline captured. Current content:\n\n{content}")
        print("First run — baseline saved, confirmation email sent.")
    elif always_email:
        send_email(f"No change — {label}", "No change.")
        print("No change — email sent (ALWAYS_EMAIL is on).")
    else:
        print("No change — no email sent.")

    with open(state_file, "w") as f:
        json.dump({"hash": new_hash, "content": content}, f, indent=2)


if __name__ == "__main__":
    main()
