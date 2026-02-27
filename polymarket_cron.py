#!/usr/bin/env python3
"""
Polymarket Cron Wrapper — sends briefing to Telegram.
Usage:
  python3 polymarket_cron.py morning
  python3 polymarket_cron.py evening
"""

import sys
import os
import subprocess
import requests

TELEGRAM_TOKEN = "8058502361:AAG1_nusRTHCvptdVVVEk-oZRa2Z03ObRkc"
TELEGRAM_CHAT = "5660486169"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def send_telegram(text: str):
    """Send message via Telegram Bot API (MarkdownV2-safe fallback)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Try Markdown first, fall back to plain text
    for parse_mode in ["Markdown", None]:
        payload = {
            "chat_id": TELEGRAM_CHAT,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                return True
            print(f"[WARN] Telegram {parse_mode}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"[ERROR] Telegram send: {e}")
    return False


def chunk_message(text: str, max_len: int = 4000) -> list[str]:
    """Split long messages into chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        # Find last newline before max_len
        cut = text[:max_len].rfind("\n")
        if cut == -1:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    scout_script = os.path.join(SCRIPT_DIR, "polymarket_scout.py")

    try:
        result = subprocess.run(
            [sys.executable, scout_script, "--mode", mode, "--days", "30", "--budget", "100"],
            capture_output=True,
            text=True,
            timeout=90
        )
        output = result.stdout.strip()
        if result.returncode != 0 or not output:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            send_telegram(f"⚠️ Polymarket scout error:\n{error_msg}")
            return

        # Send in chunks if needed
        for chunk in chunk_message(output):
            send_telegram(chunk)

    except subprocess.TimeoutExpired:
        send_telegram("⚠️ Polymarket scout timed out.")
    except Exception as e:
        send_telegram(f"⚠️ Polymarket cron error: {e}")


if __name__ == "__main__":
    main()
