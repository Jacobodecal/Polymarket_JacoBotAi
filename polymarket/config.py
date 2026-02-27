"""
Polymarket — Central Configuration
All constants, sizing rules, topic keywords, and fees in one place.
"""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPTS_DIR  = Path(__file__).parent.parent
PORTFOLIO_FILE       = SCRIPTS_DIR / "polymarket_portfolio.json"
PICKS_HISTORY_FILE   = SCRIPTS_DIR / "polymarket_picks_history.json"
PERFORMANCE_FILE     = SCRIPTS_DIR / "polymarket_performance.json"
LESSONS_FILE         = SCRIPTS_DIR / "polymarket_lessons.md"

# ── Fees & Financials ──────────────────────────────────────────────────────────
POLYMARKET_FEE = 0.02          # 2% fee on net profits at redemption

# ── Conviction Sizing (% of daily budget per tier) ────────────────────────────
SIZING = {
    "LOCK":   0.20,   # >85% probability
    "HIGH":   0.15,   # 65–85%
    "MEDIUM": 0.10,   # 45–65%
    "VALUE":  0.07,   # 30–45%
    "MOON":   0.05,   # <30%
}

# ── Resolution Type Scoring Penalties ─────────────────────────────────────────
RESOLUTION_PENALTIES = {
    "SINGLE_CANDLE": -25,  # Single 1-min candle — very high precision risk
    "TRACKER":       -5,   # Live tracker needed (e.g. tweet counts)
    "INTRADAY":      -10,  # Resolves today — need live data verification
    "EVENT":          0,   # Standard event resolution
}

# ── Topic Keywords ─────────────────────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "crypto":   ["bitcoin","btc","ethereum","eth","crypto","usdc","sol","solana","xrp",
                 "bnb","defi","nft","coinbase","binance","stablecoin","doge","microstrategy"],
    "tech":     ["ai","openai","anthropic","gpt","chatgpt","google","microsoft","apple",
                 "meta","amazon","nvidia","tesla","spacex","elon","musk","xai","deepseek",
                 "gemini","claude","grok","x.com","twitter","tech","ipo"],
    "politics": ["trump","senate","congress","election","president","republican","democrat",
                 "vote","fed","tariff","iran","russia","ukraine","nato","ceasefire",
                 "paxton","cornyn","talarico","crockett","somalia","strike","referendum",
                 "primary","nominee","parliament","chancellor","minister"],
    "macro":    ["fed","interest rate","inflation","gdp","recession","dollar","oil","gold",
                 "s&p","nasdaq","economy","unemployment","bank","cpi","fomc","tariff"],
    "culture":  ["oscar","grammy","super bowl","halftime","box office","film","movie","album",
                 "spotify","netflix","youtube","chart","trending","viral","award"],
    "sports":   ["nba","nfl","nhl","mlb","soccer","ufc","boxing","tennis","championship",
                 "playoff","world cup","league"],
}

TOPIC_PRIORITY = ["crypto", "tech", "politics", "macro", "culture"]

# ── Sports / Junk market skip keywords ────────────────────────────────────────
SKIP_KEYWORDS = [
    "nba","nfl","nhl","mlb","dota","cs2","wta ","atp "," vs. "," vs ",
    "hornets","lakers","celtics","pacers","bulls","knicks","warriors","nets",
    "heat","bucks","sixers","blazers","hawks","nuggets","clippers","suns",
    "mavericks","spurs","grizzlies","wolves","pelicans","jazz","thunder",
    "rockets","cavs","pistons","raptors","magic","wizards",
    "game 1","game 2","game 3","set 1","set 2","map 1","map 2",
    "spread:","o/u","assists","rebounds","points o/u","3-pointers",
    "t20","odi","icc ","cricket",
]

# ── Topic Emojis ───────────────────────────────────────────────────────────────
TOPIC_EMOJI = {
    "crypto":   "₿",
    "tech":     "💻",
    "politics": "🏛",
    "macro":    "📈",
    "culture":  "🎬",
    "sports":   "⚽",
}

TIER_EMOJI = {
    "LOCK":   "🔒",
    "HIGH":   "🟢",
    "MEDIUM": "🟡",
    "VALUE":  "🟠",
    "MOON":   "🚀",
}

# ── API Endpoints ──────────────────────────────────────────────────────────────
GAMMA_API     = "https://gamma-api.polymarket.com"
DATA_API      = "https://data-api.polymarket.com"
COINGECKO_API = "https://api.coingecko.com/api/v3"
XTRACKER_API  = "https://xtracker.polymarket.com/api"

# ── Default wallet ─────────────────────────────────────────────────────────────
DEFAULT_WALLET = "0xF4505fC12Fb2327f83c296a22cc0246C6a7538e4"
