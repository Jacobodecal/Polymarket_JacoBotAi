"""
Polymarket — Data Fetcher
All external API calls in one place. Clean separation from business logic.
"""

import json, requests
from datetime import datetime, timezone, timedelta
from typing import Optional
from .config import GAMMA_API, DATA_API, COINGECKO_API, XTRACKER_API

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PolyBot/2.0)"}


# ── Market Fetching ────────────────────────────────────────────────────────────

def fetch_markets(days_min: float = 0, days_max: int = 30, limit: int = 300) -> list[dict]:
    """Fetch active markets within a time window. Returns deduplicated list."""
    now = datetime.now(timezone.utc)
    min_end = now + timedelta(hours=days_min * 24)
    max_end = now + timedelta(days=days_max)
    seen = {}
    for order in ["volume24hr", "liquidity"]:
        try:
            r = requests.get(f"{GAMMA_API}/markets", params={
                "active": "true", "closed": "false", "limit": limit,
                "order": order, "ascending": "false",
                "end_date_min": min_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_date_max": max_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, timeout=TIMEOUT, headers=HEADERS)
            r.raise_for_status()
            for m in r.json():
                seen[m["id"]] = m
        except Exception as e:
            print(f"[fetcher] market fetch ({order}): {e}")
    return list(seen.values())


def fetch_market_by_slug(slug: str) -> Optional[dict]:
    """Fetch a single market by slug. Returns None if not found."""
    try:
        r = requests.get(f"{GAMMA_API}/markets", params={"slug": slug},
                         timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None
    except Exception as e:
        print(f"[fetcher] slug fetch ({slug}): {e}")
        return None


def fetch_resolution_description(slug: str) -> str:
    """Fetch the resolution description for a market. Returns empty string on failure."""
    m = fetch_market_by_slug(slug)
    return (m or {}).get("description", "") or ""


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


# ── Price Data ─────────────────────────────────────────────────────────────────

def get_crypto_prices(coins: list[str] = None) -> dict:
    """Fetch current crypto prices from CoinGecko."""
    if coins is None:
        coins = ["bitcoin", "ethereum", "solana", "ripple"]
    try:
        r = requests.get(
            f"{COINGECKO_API}/simple/price",
            params={"ids": ",".join(coins), "vs_currencies": "usd",
                    "include_24hr_change": "true"},
            timeout=10, headers=HEADERS
        )
        return r.json()
    except Exception:
        return {}


# ── Wallet / Portfolio ─────────────────────────────────────────────────────────

def get_wallet_positions(wallet: str) -> list[dict]:
    """Fetch open positions for a Polymarket wallet."""
    if not wallet:
        return []
    try:
        r = requests.get(f"{DATA_API}/positions",
                         params={"user": wallet, "sizeThreshold": "0.01"},
                         timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[fetcher] wallet positions: {e}")
    return []


def get_wallet_value(wallet: str) -> float:
    """Fetch total portfolio value for a wallet. Returns 0.0 on failure."""
    if not wallet:
        return 0.0
    try:
        r = requests.get(f"{DATA_API}/value", params={"user": wallet},
                         timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data:
                return float(data[0].get("value", 0))
    except Exception as e:
        print(f"[fetcher] wallet value: {e}")
    return 0.0


def get_wallet_pnl(wallet: str) -> dict:
    """Fetch overall P&L for a wallet."""
    if not wallet:
        return {}
    try:
        r = requests.get(f"{DATA_API}/value", params={"user": wallet},
                         timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# ── XTracker (tweet counts) ────────────────────────────────────────────────────

def get_xtracker_users() -> list[dict]:
    """Fetch all tracked users from xtracker."""
    try:
        r = requests.get(f"{XTRACKER_API}/users", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception:
        pass
    return []


def get_xtracker_tracking(tracking_id: str) -> Optional[dict]:
    """Fetch a specific tracking record from xtracker."""
    try:
        r = requests.get(f"{XTRACKER_API}/trackings/{tracking_id}",
                         headers=HEADERS, timeout=8)
        if r.status_code == 200:
            return r.json().get("data")
    except Exception:
        pass
    return None


# ── Helpers ────────────────────────────────────────────────────────────────────

def time_left(end_iso: str) -> str:
    """Human-readable time until market resolution."""
    try:
        s = end_iso.replace("Z", "+00:00")
        if "T" not in s:
            s += "T23:59:00+00:00"
        end = datetime.fromisoformat(s)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        delta = end - datetime.now(timezone.utc)
        if delta.total_seconds() < 0:
            return "EXPIRED"
        d, h = delta.days, delta.seconds // 3600
        m = (delta.seconds % 3600) // 60
        if d > 0:
            return f"{d}d {h}h"
        return f"{h}h {m}m"
    except Exception:
        return "?"


def fmt_vol(v: float) -> str:
    """Format volume/liquidity as human-readable string."""
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:.0f}"
