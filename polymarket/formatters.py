"""
Polymarket — Output Formatters
Pure formatting logic. No business logic here.
Keeps all Telegram/display concerns separate from scoring/fetching.
"""

from .config import TOPIC_EMOJI, TIER_EMOJI, POLYMARKET_FEE
from .fetcher import fmt_vol
from .resolution import analyze_market, get_warning


def format_pick(rank: int, p: dict, news_ctx: str = "") -> str:
    """Format a single pick for Telegram output."""
    q        = p["q"]
    side     = p["side"]
    entry    = p["entry"]
    tier     = p["tier"]
    topic    = p["topic"]
    suggested = p["suggested"]
    chg      = p["chg"]

    gross_ret   = (1.0 / entry - 1.0) * 100
    net_ret     = gross_ret * (1 - POLYMARKET_FEE)
    net_profit  = suggested * (1.0 / entry - 1.0) * (1 - POLYMARKET_FEE)

    te   = TOPIC_EMOJI.get(topic, "🎯")
    ce   = TIER_EMOJI.get(tier, "⚪")
    trend = "📈" if chg > 0.05 else ("📉" if chg < -0.05 else "➡️")

    lines = [
        f"*{rank}.* {te} {ce} *{q[:65]}{'…' if len(q) > 65 else ''}*",
        f"   ➡ BUY *{side}* @ {entry:.3f} → +*{net_ret:.0f}%* net (+${net_profit:.1f}) after 2% fee",
        f"   💵 Bet: *${suggested:.0f}* | {tier} conviction | Spread: {p['spread']*100:.1f}%",
        f"   💧 Liq: {fmt_vol(p['liq'])} | Vol 24h: {fmt_vol(p['v24'])} | {trend} 7d: {p['chg']*100:+.0f}% | ⏱ {p['remaining']}",
    ]

    # Reasoning
    reason = _build_reasoning(p)
    if reason:
        lines.append(f"   🧠 _{reason}_")

    # Resolution info
    res_info = analyze_market({
        "description": p.get("description", ""),
        "endDateIso":  p.get("endDateIso", ""),
        "question":    q,
        "slug":        p.get("slug", ""),
    })
    if res_info["warning"]:
        lines.append(f"   {res_info['warning']}")
    if res_info["summary"]:
        lines.append(f"   📋 _{res_info['summary'][:120]}_")

    # News context
    if news_ctx:
        lines.append(f"   {news_ctx}")

    lines.append(f"   🔗 polymarket.com/event/{p['slug']}\n")
    return "\n".join(lines)


def _build_reasoning(p: dict) -> str:
    """Generate human-readable reasoning for a pick."""
    parts = []
    entry = p["entry"]
    chg   = p["chg"]
    liq   = p["liq"]

    # Probability context
    if entry >= 0.85:
        parts.append(f"near-certain at {entry*100:.0f}% — high-confidence anchor")
    elif entry >= 0.65:
        parts.append(f"strong probability ({entry*100:.0f}%) with solid upside")
    elif entry >= 0.45:
        parts.append(f"coin-flip ({entry*100:.0f}%) with good return potential")
    elif entry >= 0.25:
        parts.append(f"underdog ({entry*100:.0f}%) — asymmetric upside if correct")
    else:
        parts.append(f"moonshot ({entry*100:.0f}%) — small bet, high multiplier")

    # Momentum
    if chg >= 0.20:
        parts.append(f"smart money piling in (+{chg*100:.0f}% in 7d)")
    elif chg >= 0.10:
        parts.append(f"positive momentum (+{chg*100:.0f}% this week)")
    elif chg <= -0.20:
        parts.append(f"market collapsing on this side ({chg*100:.0f}% in 7d) — contrarian value")
    elif chg <= -0.10:
        parts.append(f"recent selloff ({chg*100:.0f}%) creates value entry")

    # Liquidity
    if liq >= 50_000:
        parts.append("deep liquidity = easy exit anytime")
    elif liq < 8_000:
        parts.append("thin liquidity — plan to hold to resolution")

    return "; ".join(parts[:3])


def format_progress_header(portfolio: dict, daily_budget: float, day1: bool = False) -> str:
    """Format the header section of the morning briefing."""
    from datetime import datetime, timezone, timedelta
    from .fetcher import get_crypto_prices

    now_sp = datetime.now(timezone.utc) + timedelta(hours=-3)
    bankroll = portfolio.get("bankroll", 300)
    goal     = portfolio.get("goal", 1000)
    pnl      = bankroll - 300

    pct    = min((bankroll / goal) * 100, 100)
    filled = int(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)

    prices = get_crypto_prices(["bitcoin", "ethereum"])
    btc = prices.get("bitcoin", {})
    eth = prices.get("ethereum", {})

    lines = []
    if day1:
        lines.append("🚀 *POLYMARKET — DAY 1 LAUNCH*")
        lines.append(f"_{now_sp.strftime('%A, %b %d — %I:%M %p')} (SP)_")
        lines.append("_Full portfolio deployment — let's get it_ 💪\n")
    else:
        lines.append("🌅 *POLYMARKET MORNING PICKS*")
        lines.append(f"_{now_sp.strftime('%A, %b %d — %I:%M %p')} (SP)_\n")

    lines.append(f"🎯 [{bar}] ${bankroll:.0f} / ${goal:.0f} ({pct:.0f}%) | PnL: {pnl:+.0f}")

    if btc:
        lines.append(f"📊 BTC ${btc.get('usd',0):,.0f} ({btc.get('usd_24h_change',0):+.1f}%) | "
                     f"ETH ${eth.get('usd',0):,.0f} ({eth.get('usd_24h_change',0):+.1f}%)")

    lines.append(f"💵 Budget today: *${daily_budget:.0f}*"
                 + (" — deploying full bankroll!" if day1 else " — distribute by conviction"))

    return "\n".join(lines)
