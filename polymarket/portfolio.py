"""
Polymarket — Portfolio Manager
Handles all portfolio state: loading, saving, position tracking, PnL.
"""

import json
from datetime import datetime, timezone, timedelta
from .config import PORTFOLIO_FILE, POLYMARKET_FEE, DEFAULT_WALLET
from .fetcher import get_wallet_positions, get_wallet_value, get_crypto_prices, fmt_vol, time_left


def _sp_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=-3)


def load() -> dict:
    """Load portfolio from disk. Returns default state if not found."""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE) as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return {
        "bankroll":     300.0,
        "cash":         300.0,
        "positions":    [],
        "closed_trades":[],
        "total_pnl":    0.0,
        "goal":         1000.0,
        "start_date":   _sp_now().strftime("%Y-%m-%d"),
        "wallet":       DEFAULT_WALLET,
        "polymarket_fee": POLYMARKET_FEE,
        "day1_deploy":  False,
        "daily_budget": 100.0,
    }


def save(portfolio: dict):
    """Save portfolio to disk."""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def get_live_snapshot(portfolio: dict) -> dict:
    """
    Fetch live position data from wallet and return enriched snapshot.
    Returns dict with: positions, total_invested, total_current, open_pnl, cash, total_value
    """
    wallet = portfolio.get("wallet") or DEFAULT_WALLET
    cash   = portfolio.get("cash", 0)

    positions = get_wallet_positions(wallet)
    total_invested = sum(float(p.get("initialValue", 0)) for p in positions)
    total_current  = sum(float(p.get("currentValue", 0)) for p in positions)
    open_pnl       = total_current - total_invested

    return {
        "positions":       positions,
        "total_invested":  round(total_invested, 2),
        "total_current":   round(total_current, 2),
        "open_pnl":        round(open_pnl, 2),
        "cash":            cash,
        "total_value":     round(cash + total_current, 2),
        "wallet":          wallet,
    }


def progress_bar(bankroll: float, goal: float) -> str:
    """Generate ASCII progress bar."""
    pct = min((bankroll / goal) * 100, 100)
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {pct:.0f}%"


def format_snapshot(portfolio: dict, snap: dict) -> str:
    """Format a live portfolio snapshot for Telegram."""
    bankroll  = portfolio.get("bankroll", 300)
    goal      = portfolio.get("goal", 1000)
    start_pnl = snap["total_value"] - bankroll

    prices = get_crypto_prices(["bitcoin", "ethereum"])
    btc = prices.get("bitcoin", {})
    eth = prices.get("ethereum", {})

    now_sp = _sp_now()
    lines = [
        f"📊 *PORTFOLIO SNAPSHOT*",
        f"_{now_sp.strftime('%A, %b %d — %I:%M %p')} (SP)_\n",
        f"🎯 {progress_bar(snap['total_value'], goal)} ${snap['total_value']:.2f} / ${goal:.0f}",
        f"💰 Cash: ${snap['cash']:.2f} | Positions: ${snap['total_current']:.2f}",
        f"📈 Open PnL: ${snap['open_pnl']:+.2f} | Day PnL: ${start_pnl:+.2f}",
    ]

    if btc:
        lines.append(f"₿ BTC ${btc.get('usd',0):,.0f} ({btc.get('usd_24h_change',0):+.1f}%) | "
                     f"ETH ${eth.get('usd',0):,.0f} ({eth.get('usd_24h_change',0):+.1f}%)")

    if snap["positions"]:
        lines.append(f"\n*Open Positions ({len(snap['positions'])}):*")
        for p in snap["positions"]:
            iv   = float(p.get("initialValue", 0))
            cv   = float(p.get("currentValue", 0))
            pnl  = cv - iv
            pct  = float(p.get("percentPnl", 0))
            end  = p.get("endDate", "")
            rem  = time_left(end) if end else "?"
            icon = "🟢" if pnl >= 0 else "🔴"
            title = p.get("title", "?")[:48]
            lines.append(f"{icon} *{p['outcome']}* on _{title}_")
            lines.append(f"   ${iv:.2f} → ${cv:.2f} ({pnl:+.2f}, {pct:+.1f}%) | ⏱ {rem}")
    else:
        lines.append("\n_No open positions_")

    return "\n".join(lines)
