"""
Polymarket — Main Orchestrator
Thin coordinator: fetches data, scores picks, formats output.
All business logic lives in the specialized modules.
"""

from .config import POLYMARKET_FEE, PICKS_HISTORY_FILE, LESSONS_FILE
from .fetcher import fetch_markets, get_crypto_prices, fmt_vol, time_left
from .scorer import build_picks, detect_topic, is_skip, get_prices, pick_side
from .portfolio import load as load_portfolio, save as save_portfolio, get_live_snapshot, format_snapshot
from .formatters import format_pick, format_progress_header
from .performance import record_pick as perf_record_pick
from .news import fetch_all_news_parallel, format_news_context, news_summary
from .resolution import analyze_market

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _sp_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=-3)


def _load_lessons() -> str:
    """Load lessons file for context — reminds algorithm of past mistakes."""
    if LESSONS_FILE.exists():
        text = LESSONS_FILE.read_text()
        # Extract just the Golden Rules section for compactness
        if "## Golden Rules" in text:
            return text.split("## Golden Rules")[1][:500]
    return ""


def morning_briefing(daily_budget: float = 100.0, days_max: int = 30) -> str:
    """
    Generate morning picks report.
    Full pipeline: fetch → score → news → format → record.
    """
    portfolio = load_portfolio()
    bankroll  = portfolio.get("bankroll", 300.0)
    cash      = portfolio.get("cash", 300.0)
    day1      = portfolio.get("day1_deploy", False)

    if day1:
        daily_budget = cash

    # Fetch markets (skip today-only for cleaner picks; intraday gets penalized in scorer)
    markets = fetch_markets(days_min=0, days_max=days_max)

    # Fetch news in parallel
    try:
        news = fetch_all_news_parallel()
    except Exception:
        news = {}

    # Score and select picks
    picks = build_picks(markets, daily_budget=daily_budget, n=10)

    lines = []

    # Header
    lines.append(format_progress_header(portfolio, daily_budget, day1=day1))
    lines.append("")

    # News summary
    if news:
        summary = news_summary(news)
        if summary:
            lines.append("📡 *Morning Intelligence Scan*")
            lines.append(summary)
            lines.append("")

    if not picks:
        lines.append("📭 No strong opportunities found today. Markets are quiet.")
        return "\n".join(lines)

    header = ("🚀 *FULL DEPLOYMENT PICKS*" if day1
              else f"🎯 *TOP {len(picks)} PICKS — ${daily_budget:.0f} budget*")
    lines.append(header + "\n")

    for rank, p in enumerate(picks, 1):
        # Attach resolution analysis
        res = analyze_market({
            "description": p.get("description", ""),
            "endDateIso":  p.get("endDateIso", ""),
            "question":    p["q"],
            "slug":        p["slug"],
        })
        p["resolution_type"] = res["type"]

        # News context
        news_ctx = format_news_context(p["q"], news) if news else ""

        lines.append(format_pick(rank, p, news_ctx=news_ctx))

        # Record to performance tracker
        try:
            perf_record_pick(p)
        except Exception:
            pass

    # Save picks history
    _save_picks_history(picks)

    # Footer
    lines.append("─" * 28)
    lines.append("📝 _Tell me your bets — I'll log the portfolio_")
    if not portfolio.get("wallet"):
        lines.append("🔑 _Share your Polymarket wallet for auto-tracking_")

    return "\n".join(lines)


def evening_review(days_max: int = 30) -> str:
    """
    Generate evening portfolio review + overnight watchlist.
    """
    portfolio = load_portfolio()
    snap      = get_live_snapshot(portfolio)

    lines = [format_snapshot(portfolio, snap), ""]

    # Overnight watchlist (3 picks)
    markets = fetch_markets(days_min=0.5, days_max=days_max)
    try:
        news = fetch_all_news_parallel()
    except Exception:
        news = {}

    picks = build_picks(markets, daily_budget=100, n=3)

    lines.append("─" * 28)
    lines.append("🔭 *Overnight Watchlist — 3 Picks*")
    lines.append("_Markets to watch before tomorrow_\n")

    for rank, p in enumerate(picks, 1):
        news_ctx = format_news_context(p["q"], news) if news else ""
        lines.append(format_pick(rank, p, news_ctx=news_ctx))

    lines.append("─" * 28)
    lines.append("📝 _Tell me any trades from today — I'll update the portfolio_")

    return "\n".join(lines)


def portfolio_snapshot() -> str:
    """Quick live portfolio snapshot."""
    portfolio = load_portfolio()
    snap      = get_live_snapshot(portfolio)
    return format_snapshot(portfolio, snap)


def _save_picks_history(picks: list[dict]):
    """Append today's picks to history file."""
    history = []
    if PICKS_HISTORY_FILE.exists():
        try:
            with open(PICKS_HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append({
        "date":  _sp_now().strftime("%Y-%m-%d"),
        "picks": [
            {
                "q": p["q"], "side": p["side"], "entry": p["entry"],
                "tier": p["tier"], "topic": p["topic"],
                "slug": p["slug"], "suggested": p["suggested"],
                "resolution_type": p.get("resolution_type", "EVENT"),
            }
            for p in picks
        ],
    })

    with open(PICKS_HISTORY_FILE, "w") as f:
        json.dump(history[-60:], f, indent=2)  # keep last 60 days
