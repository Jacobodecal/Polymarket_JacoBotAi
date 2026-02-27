"""
Polymarket — Performance Tracker
Records every pick and resolution. Calculates edge by topic/tier/type.
This is how the algorithm improves over time.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from .config import PERFORMANCE_FILE


def _load() -> list[dict]:
    if PERFORMANCE_FILE.exists():
        try:
            with open(PERFORMANCE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(records: list[dict]):
    with open(PERFORMANCE_FILE, "w") as f:
        json.dump(records, f, indent=2)


def record_pick(pick: dict):
    """
    Record a pick at bet time.
    Call this when picks are generated (before resolution).
    """
    records = _load()
    record = {
        "id":               pick.get("slug", ""),
        "date":             datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "question":         pick.get("q", ""),
        "slug":             pick.get("slug", ""),
        "side":             pick.get("side", ""),
        "entry_price":      pick.get("entry", 0),
        "suggested_bet":    pick.get("suggested", 0),
        "topic":            pick.get("topic", ""),
        "tier":             pick.get("tier", ""),
        "resolution_type":  pick.get("resolution_type", "EVENT"),
        "score":            round(pick.get("score", 0), 2),
        "momentum_7d":      pick.get("chg", 0),
        "liquidity":        pick.get("liq", 0),
        "volume_24h":       pick.get("v24", 0),
        "end_date":         pick.get("endDateIso", "")[:10],
        # Filled in at resolution:
        "resolved":         False,
        "resolved_date":    None,
        "won":              None,
        "actual_pnl":       None,
        "return_pct":       None,
    }
    # Avoid duplicate records for same slug+date
    existing_ids = {(r["slug"], r["date"]) for r in records}
    if (record["slug"], record["date"]) not in existing_ids:
        records.append(record)
        _save(records)


def record_resolution(slug: str, won: bool, actual_pnl: float, bet_amount: float = 0):
    """
    Update a pick record when the market resolves.
    Call this from the evening review or when a market closes.
    """
    records = _load()
    updated = False
    for r in records:
        if r["slug"] == slug and not r["resolved"]:
            r["resolved"]      = True
            r["resolved_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            r["won"]           = won
            r["actual_pnl"]    = round(actual_pnl, 2)
            if bet_amount > 0:
                r["return_pct"] = round((actual_pnl / bet_amount) * 100, 1)
            updated = True
            break
    if updated:
        _save(records)
    return updated


def get_stats() -> dict:
    """
    Calculate performance statistics across all resolved picks.
    Returns edge analysis by topic, tier, and resolution type.
    """
    records = [r for r in _load() if r.get("resolved") and r.get("won") is not None]
    if not records:
        return {"error": "No resolved picks yet"}

    total = len(records)
    wins  = sum(1 for r in records if r["won"])
    pnl   = sum(r.get("actual_pnl", 0) for r in records)

    def group_stats(key: str) -> dict:
        groups = {}
        for r in records:
            g = r.get(key, "unknown")
            if g not in groups:
                groups[g] = {"total": 0, "wins": 0, "pnl": 0.0}
            groups[g]["total"] += 1
            groups[g]["wins"]  += 1 if r["won"] else 0
            groups[g]["pnl"]   += r.get("actual_pnl", 0)
        return {
            k: {
                "win_rate": round(v["wins"] / v["total"] * 100, 1),
                "total_picks": v["total"],
                "total_pnl": round(v["pnl"], 2),
            }
            for k, v in groups.items()
        }

    return {
        "total_picks":  total,
        "win_rate":     round(wins / total * 100, 1),
        "total_pnl":    round(pnl, 2),
        "by_topic":     group_stats("topic"),
        "by_tier":      group_stats("tier"),
        "by_resolution_type": group_stats("resolution_type"),
    }


def format_performance_report() -> str:
    """Human-readable performance report for Telegram."""
    stats = get_stats()
    if "error" in stats:
        return f"📊 No resolved picks yet — check back after first resolutions."

    lines = [
        f"📊 *PERFORMANCE REPORT*",
        f"Picks: {stats['total_picks']} | Win rate: {stats['win_rate']}% | PnL: ${stats['total_pnl']:+.2f}",
        "",
        "*By Topic:*",
    ]
    for topic, s in sorted(stats["by_topic"].items(), key=lambda x: -x[1]["win_rate"]):
        lines.append(f"  {topic}: {s['win_rate']}% wins ({s['total_picks']} picks) | PnL ${s['total_pnl']:+.2f}")

    lines.append("\n*By Conviction Tier:*")
    for tier, s in sorted(stats["by_tier"].items(), key=lambda x: -x[1]["win_rate"]):
        lines.append(f"  {tier}: {s['win_rate']}% wins ({s['total_picks']} picks) | PnL ${s['total_pnl']:+.2f}")

    lines.append("\n*By Resolution Type:*")
    for rt, s in sorted(stats["by_resolution_type"].items(), key=lambda x: -x[1]["win_rate"]):
        lines.append(f"  {rt}: {s['win_rate']}% wins ({s['total_picks']} picks) | PnL ${s['total_pnl']:+.2f}")

    return "\n".join(lines)
