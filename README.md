# 🎯 Polymarket JacoBotAi

> AI-powered prediction market engine for Polymarket — built by JacoBot AI, managed by Jacobo De Cal.

**Goal:** $300 → $1,000 by end of March 2026 through systematic, data-driven prediction market betting.

---

## Architecture

```
polymarket/                 # Core engine (v2.0)
├── config.py               # Constants: sizing, fees, keywords, penalties
├── fetcher.py              # API layer: Gamma API, CoinGecko, wallet tracking
├── resolution.py           # Resolution rule parser — classifies every market
├── scorer.py               # Scoring engine — ranks markets by edge potential
├── portfolio.py            # Live portfolio & wallet tracking
├── performance.py          # Pick history + edge analytics over time
├── formatters.py           # Telegram output formatting
├── news/
│   └── fetcher.py          # Parallel news from 20+ RSS + Reddit + CryptoPanic
└── models/
    └── tweet_count.py      # Hourly-weighted tweet count projector (Elon markets)

polymarket_scout.py         # Entry point (thin wrapper)
polymarket_cron.py          # Cron runner for automated daily picks
polymarket_lessons.md       # Lessons learned — updated after every mistake
```

---

## How It Works

### Morning Picks (9 AM São Paulo)
1. Fetches all active Polymarket markets via Gamma API
2. Fetches news from 20+ sources in parallel (RSS, Reddit, CryptoPanic)
3. Scores each market using composite signal:
   - Probability quality (genuine uncertainty = edge)
   - Liquidity + volume (market health)
   - 7-day momentum (strongest alpha signal)
   - Resolution type penalties (single-candle bets penalized -25pts)
   - Topic relevance
4. Selects top 10 picks with conviction-based sizing
5. Shows: reasoning + resolution rules summary + relevant news + ⚠️ warnings

### Evening Review (9 PM São Paulo)
- Live portfolio snapshot via wallet API
- P&L update on all positions
- Overnight watchlist (3 picks)

### Performance Tracking
Every pick is recorded with: topic, tier, resolution type, entry price, momentum signal.  
On resolution: win/loss + actual P&L logged.  
Over time: win rate by topic/tier/resolution type → identifies where real edge exists.

---

## Resolution Type Classification

| Type | Description | Score Penalty |
|------|-------------|---------------|
| `EVENT` | Standard event resolution | 0 |
| `TRACKER` | Live tracker needed (tweet counts) | -5 |
| `INTRADAY` | Resolves within 24h | -10 |
| `SINGLE_CANDLE` | Single 1-min Binance candle at noon ET | -25 |

---

## Conviction Tiers & Sizing

| Tier | Probability | Budget % |
|------|-------------|----------|
| LOCK | >85% | 20% |
| HIGH | 65–85% | 15% |
| MEDIUM | 45–65% | 10% |
| VALUE | 30–45% | 7% |
| MOON | <30% | 5% |

All returns shown net of Polymarket's **2% fee on profits**.

---

## Key Lessons (Day 1 — Feb 27, 2026)

1. **Read resolution rules for every pick. No exceptions.**
2. **Intraday markets: check live data before betting.**
3. **Political primaries: check full multi-candidate market — volume beats polls.**
4. **High-volume markets (>$500K) know more than any news headline.**
5. **Single-candle BTC bets are precision bets, not direction bets.**
6. **Verify exact market title + end date before linking.**
7. **Never flip-flop without new data.**

Full lessons: [`polymarket_lessons.md`](./polymarket_lessons.md)

---

## Setup

```bash
pip install requests

# Run morning picks
python3 polymarket_scout.py --mode morning

# Run evening review
python3 polymarket_scout.py --mode evening

# Live portfolio snapshot
python3 polymarket_scout.py --mode portfolio
```

### Portfolio Config
Copy `portfolio.example.json` → `polymarket_portfolio.json` and set your wallet address.

---

## Roadmap

- [ ] BTC price model (hourly momentum, macro indicators)
- [ ] Political market analyzer (multi-candidate, polling data)
- [ ] Backtesting framework
- [ ] Auto-resolution detection (mark picks as won/lost automatically)
- [ ] Edge report (weekly analysis of where we're winning)
- [ ] Web dashboard

---

*Built by JacoBot AI — improving with every trade.*
