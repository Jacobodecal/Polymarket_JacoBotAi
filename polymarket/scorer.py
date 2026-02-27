"""
Polymarket — Market Scoring Engine
Scores markets for edge potential. Higher = better opportunity.
Penalizes high-precision/intraday markets. Rewards liquidity + momentum.
"""

import json
from datetime import datetime, timezone
from .config import TOPIC_KEYWORDS, TOPIC_PRIORITY, SKIP_KEYWORDS, SIZING, RESOLUTION_PENALTIES
from .resolution import classify as classify_resolution


def detect_topic(question: str) -> str:
    """Detect the topic of a market question."""
    ql = question.lower()
    for topic in TOPIC_PRIORITY + ["sports"]:
        for kw in TOPIC_KEYWORDS.get(topic, []):
            if kw in ql:
                return topic
    return "other"


def is_skip(question: str) -> bool:
    """Return True if this market should be skipped (sports noise etc.)."""
    ql = question.lower()
    return any(kw in ql for kw in SKIP_KEYWORDS)


def get_prices(m: dict) -> tuple[float, float]:
    """Parse YES/NO prices from a market dict."""
    try:
        arr = json.loads(m.get("outcomePrices", "[0.5,0.5]")) \
              if isinstance(m.get("outcomePrices"), str) else m.get("outcomePrices", [0.5, 0.5])
        yes = float(arr[0]) if arr else 0.5
        no  = float(arr[1]) if len(arr) > 1 else 1 - yes
        return yes, no
    except Exception:
        return 0.5, 0.5


def conviction_tier(yes_price: float, side: str) -> str:
    """Map probability of winning to a conviction tier."""
    p = yes_price if side == "YES" else (1 - yes_price)
    if p >= 0.85: return "LOCK"
    if p >= 0.65: return "HIGH"
    if p >= 0.45: return "MEDIUM"
    if p >= 0.30: return "VALUE"
    return "MOON"


def pick_side(yes_p: float, chg: float) -> tuple[str, float]:
    """
    Select which side to bet on.
    Momentum-first: if strong 7d move, follow it.
    Otherwise, pick the underdog side (higher return).
    """
    if chg >= 0.12:
        return "YES", yes_p
    if chg <= -0.12:
        return "NO", 1 - yes_p
    if yes_p <= 0.5:
        return "YES", yes_p
    return "NO", 1 - yes_p


def score_market(m: dict) -> float:
    """
    Score a market for betting opportunity.
    Returns a float score — higher is better.
    Returns -999 for markets that should be filtered out.

    Key signals (in order of importance):
      1. Probability quality (is there genuine uncertainty with edge?)
      2. Liquidity (can we enter/exit cleanly?)
      3. Volume (market health, price reliability)
      4. Momentum (7-day price change — strongest alpha signal)
      5. Resolution type (penalize precision bets)
      6. Spread cost
      7. Time horizon
    """
    yes_p, no_p = get_prices(m)
    v24    = float(m.get("volume24hr") or 0)
    liq    = float(m.get("liquidityNum") or m.get("liquidity") or 0)
    spread = float(m.get("spread") or 0.5)
    chg    = float(m.get("oneWeekPriceChange") or 0)
    end    = m.get("endDateIso", "")[:10]
    desc   = m.get("description", "") or ""

    side, entry = pick_side(yes_p, chg)

    # Hard filters
    if entry < 0.07 or entry > 0.97: return -999
    if liq < 5_000:                   return -999

    return_pct = (1.0 / entry - 1.0) * 100

    score = 0.0

    # ── Probability quality ────────────────────────────────────────────────────
    if 0.25 <= entry <= 0.75:   score += 35
    elif 0.15 <= entry < 0.25:  score += 22
    elif 0.75 < entry <= 0.85:  score += 28
    elif 0.85 < entry <= 0.93:  score += 18
    elif 0.93 < entry <= 0.97:  score += 8

    # ── Liquidity ──────────────────────────────────────────────────────────────
    if liq >= 100_000:  score += 30
    elif liq >= 30_000: score += 22
    elif liq >= 10_000: score += 14
    elif liq >= 5_000:  score += 7

    # ── Volume ────────────────────────────────────────────────────────────────
    if v24 >= 200_000:  score += 22
    elif v24 >= 50_000: score += 16
    elif v24 >= 10_000: score += 9
    elif v24 >= 3_000:  score += 4

    # ── Spread cost ───────────────────────────────────────────────────────────
    if spread < 0.01:   score += 18
    elif spread < 0.02: score += 12
    elif spread < 0.03: score += 7
    elif spread < 0.05: score += 3
    elif spread > 0.05: score -= 10

    # ── Momentum (strongest alpha signal) ────────────────────────────────────
    abs_chg = abs(chg)
    if abs_chg >= 0.30:   score += 28
    elif abs_chg >= 0.15: score += 20
    elif abs_chg >= 0.08: score += 12
    elif abs_chg >= 0.03: score += 6

    # ── Return potential (balanced) ───────────────────────────────────────────
    if 30 <= return_pct <= 80:    score += 15
    elif 80 < return_pct <= 200:  score += 10
    elif 15 <= return_pct < 30:   score += 8
    elif return_pct > 200:        score += 5
    elif return_pct < 15:         score += 6

    # ── Topic relevance ────────────────────────────────────────────────────────
    topic = detect_topic(m.get("question", ""))
    if topic in ["crypto", "tech", "politics"]: score += 10
    elif topic == "macro":                       score += 7
    elif topic == "culture":                     score += 4

    # ── Time horizon ──────────────────────────────────────────────────────────
    try:
        s = end + "T23:59:00+00:00" if "T" not in end else end.replace("Z", "+00:00")
        end_dt = datetime.fromisoformat(s)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        days = (end_dt - datetime.now(timezone.utc)).days
        if days <= 1:    score += 12
        elif days <= 3:  score += 8
        elif days <= 7:  score += 4
        elif days > 21:  score -= 5
    except Exception:
        pass

    # ── Resolution type penalty (Day 1 lesson) ────────────────────────────────
    res_type = classify_resolution(desc, m.get("endDateIso", ""))
    score += RESOLUTION_PENALTIES.get(res_type, 0)

    return score


def build_picks(markets: list[dict], daily_budget: float, n: int = 10) -> list[dict]:
    """
    Score, filter, and size picks from a list of markets.
    Returns top-n picks with all computed fields.
    """
    scored = []
    for m in markets:
        q = m.get("question", "")
        if is_skip(q):
            continue
        topic = detect_topic(q)
        if topic == "other":
            continue
        s = score_market(m)
        if s > 20:
            scored.append((s, m, topic))

    scored.sort(key=lambda x: -x[0])
    top = scored[:n]

    # Compute sides and raw sizes
    picks = []
    for score, m, topic in top:
        q     = m.get("question", "")
        yes_p, no_p = get_prices(m)
        liq   = float(m.get("liquidityNum") or m.get("liquidity") or 0)
        v24   = float(m.get("volume24hr") or 0)
        spread = float(m.get("spread") or 0)
        chg   = float(m.get("oneWeekPriceChange") or 0)

        side, entry = pick_side(yes_p, chg)
        tier = conviction_tier(yes_p, side)
        raw_size = daily_budget * SIZING.get(tier, 0.10)

        picks.append({
            "score": score, "q": q, "topic": topic,
            "yes_p": yes_p, "no_p": no_p,
            "side": side, "entry": entry, "tier": tier,
            "liq": liq, "v24": v24, "spread": spread, "chg": chg,
            "remaining": __import__('polymarket.fetcher', fromlist=['time_left']).time_left(m.get("endDateIso", "")),
            "slug": m.get("slug", ""),
            "endDateIso": m.get("endDateIso", ""),
            "description": m.get("description", "") or "",
            "raw_size": raw_size,
        })

    # Normalize sizes to daily_budget
    total_raw = sum(p["raw_size"] for p in picks) or 1
    for p in picks:
        raw = p["raw_size"] * (daily_budget / total_raw)
        p["suggested"] = max(5.0, round(raw / 5) * 5)

    return picks
