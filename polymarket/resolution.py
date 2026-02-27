"""
Polymarket — Resolution Rule Parser
Reads, classifies, and summarizes how each market resolves.
Critical for avoiding the "wrong resolution assumptions" mistake from Day 1.
"""

import re
from datetime import datetime, timezone
from .fetcher import fetch_resolution_description


# ── Classification ─────────────────────────────────────────────────────────────

def classify(description: str, end_date_iso: str = "") -> str:
    """
    Classify how a market resolves.
    Returns: SINGLE_CANDLE | TRACKER | INTRADAY | EVENT
    """
    desc = description.lower()

    # Single 1-minute candle (BTC price ranges etc.)
    if "1 minute candle" in desc or "1m candle" in desc or "close\" price" in desc:
        return "SINGLE_CANDLE"

    # Tracker-based (tweet/post counters)
    if any(kw in desc for kw in ["tracker", "xtracker", "post counter", "tweet counter"]):
        return "TRACKER"

    # Intraday: resolves within next 20 hours
    if end_date_iso:
        try:
            s = end_date_iso.replace("Z", "+00:00")
            if "T" not in s:
                s += "T23:59:00+00:00"
            end_dt = datetime.fromisoformat(s)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            hours_left = (end_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_left < 20:
                return "INTRADAY"
        except Exception:
            pass

    return "EVENT"


def summarize(description: str, question: str = "") -> str:
    """
    Return a 1-sentence plain English summary of how the market resolves.
    Extracts the key resolution criteria from the description.
    """
    if not description:
        return ""

    desc = description.strip()

    # Try to extract the first meaningful resolution sentence
    sentences = re.split(r'(?<=[.!?])\s+', desc)

    # Find the most informative sentence (has resolution trigger words)
    TRIGGER_WORDS = ["resolve", "will resolve", "resolves to", "yes if", "no if",
                     "qualifying", "defined as", "source for this"]

    for sent in sentences[:6]:
        sent_l = sent.lower()
        if any(tw in sent_l for tw in TRIGGER_WORDS):
            # Clean up and return
            clean = re.sub(r'\s+', ' ', sent).strip()
            if len(clean) > 20:
                return clean[:200] + ("…" if len(clean) > 200 else "")

    # Fallback: return first sentence
    if sentences:
        clean = re.sub(r'\s+', ' ', sentences[0]).strip()
        return clean[:200] + ("…" if len(clean) > 200 else "")

    return ""


def get_warning(res_type: str) -> str:
    """Return a ⚠️ warning string for risky resolution types."""
    warnings = {
        "SINGLE_CANDLE": "⚠️ Resolves on a SINGLE 1-min candle at noon ET — not end of day. High precision risk.",
        "TRACKER":       "⚠️ Resolves via live TRACKER — check current count before betting.",
        "INTRADAY":      "⚠️ Resolves TODAY — verify live data before entering.",
    }
    return warnings.get(res_type, "")


def analyze_market(m: dict) -> dict:
    """
    Full resolution analysis for a market dict.
    Returns dict with: type, summary, warning, description
    """
    desc    = m.get("description", "") or ""
    end     = m.get("endDateIso", "") or ""
    q       = m.get("question", "") or ""
    slug    = m.get("slug", "") or ""

    # If description is missing, try to fetch it
    if not desc and slug:
        desc = fetch_resolution_description(slug)

    res_type = classify(desc, end)
    summary  = summarize(desc, q)
    warning  = get_warning(res_type)

    return {
        "type":        res_type,
        "summary":     summary,
        "warning":     warning,
        "description": desc[:500],
    }
