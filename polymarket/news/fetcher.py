#!/usr/bin/env python3
"""
Polymarket News Intelligence — Multi-source research engine.
Fetches headlines, context, and signals from 20+ free sources.
Used by polymarket_scout.py to annotate each pick with real news.
"""

import requests, json, re, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}


# ─── RSS Fetcher ─────────────────────────────────────────────────────────────

def fetch_rss(url: str, max_items: int = 10, label: str = "") -> list[dict]:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            desc  = (item.findtext("description") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            if title:
                items.append({"title": title, "desc": desc[:200], "link": link,
                               "pub": pub, "source": label})
            if len(items) >= max_items:
                break
        return items
    except Exception as e:
        return []


# ─── Reddit Fetcher ──────────────────────────────────────────────────────────

def fetch_reddit(subreddit: str, sort: str = "hot", limit: int = 15) -> list[dict]:
    try:
        r = requests.get(
            f"https://www.reddit.com/r/{subreddit}/{sort}.json",
            params={"limit": limit},
            headers={**HEADERS, "Accept": "application/json"},
            timeout=TIMEOUT
        )
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        items = []
        for p in posts:
            d = p.get("data", {})
            title = d.get("title","").strip()
            score = d.get("score", 0)
            comments = d.get("num_comments", 0)
            flair = d.get("link_flair_text","") or ""
            url = d.get("url","")
            if title and not d.get("stickied"):
                items.append({
                    "title": title, "score": score, "comments": comments,
                    "flair": flair, "link": url, "source": f"r/{subreddit}"
                })
        return items
    except:
        return []


# ─── CryptoPanic ─────────────────────────────────────────────────────────────

def fetch_cryptopanic(kind: str = "news", max_items: int = 15) -> list[dict]:
    """Fetch crypto news/media from CryptoPanic (no API key for public posts)."""
    try:
        r = requests.get(
            "https://cryptopanic.com/api/v1/posts/",
            params={"auth_token": "public", "public": "true", "kind": kind},
            timeout=TIMEOUT
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            items = []
            for p in results[:max_items]:
                title = p.get("title","").strip()
                domain = (p.get("domain","") or "").strip()
                pub = p.get("published_at","")
                votes = p.get("votes", {})
                bull = votes.get("positive", 0)
                bear = votes.get("negative", 0)
                items.append({
                    "title": title, "source": domain,
                    "bullish": bull, "bearish": bear, "pub": pub
                })
            return items
    except:
        pass
    return []


# ─── Free Financial/News APIs ────────────────────────────────────────────────

def fetch_newsdata_rss(query: str, max_items: int = 8) -> list[dict]:
    """Google News RSS — free, no key."""
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    return fetch_rss(url, max_items, f"GoogleNews:{query[:20]}")


def fetch_gnews_topic(topic_id: str, max_items: int = 8) -> list[dict]:
    """Google News RSS by topic ID."""
    url = f"https://news.google.com/rss/topics/{topic_id}?hl=en-US&gl=US&ceid=US:en"
    return fetch_rss(url, max_items, f"GoogleNews:{topic_id[:10]}")


# ─── All Sources ─────────────────────────────────────────────────────────────

RSS_FEEDS = {
    # Crypto
    "cointelegraph":    ("https://cointelegraph.com/rss", 10),
    "coindesk":         ("https://www.coindesk.com/arc/outboundfeeds/rss/", 10),
    "decrypt":          ("https://decrypt.co/feed", 8),
    "theblock":         ("https://www.theblock.co/rss.xml", 8),
    # Finance / Macro
    "reuters_finance":  ("https://feeds.reuters.com/reuters/businessNews", 8),
    "ft_markets":       ("https://www.ft.com/markets?format=rss", 6),
    "bloomberg_mkt":    ("https://feeds.bloomberg.com/markets/news.rss", 6),
    "wsj_markets":      ("https://feeds.a.dj.com/rss/RSSMarketsMain.xml", 6),
    # General / Politics / World
    "bbc_world":        ("https://feeds.bbci.co.uk/news/world/rss.xml", 8),
    "reuters_world":    ("https://feeds.reuters.com/Reuters/worldNews", 8),
    "ap_politics":      ("https://rss.ap.org/it/politics-news", 6),
    "guardian_world":   ("https://www.theguardian.com/world/rss", 6),
    # US Politics
    "politico":         ("https://www.politico.com/rss/politicopicks.xml", 6),
    "thehill":          ("https://thehill.com/news/feed/", 6),
    # Tech / AI
    "techcrunch":       ("https://techcrunch.com/feed/", 6),
    "verge":            ("https://www.theverge.com/rss/index.xml", 6),
    "ars_tech":         ("https://feeds.arstechnica.com/arstechnica/technology-lab", 6),
}

REDDIT_SUBS = [
    ("worldnews", "hot", 15),
    ("politics", "hot", 12),
    ("investing", "hot", 12),
    ("CryptoCurrency", "hot", 15),
    ("Bitcoin", "hot", 10),
    ("ethereum", "hot", 8),
    ("polymarket", "hot", 20),  # most relevant!
    ("geopolitics", "hot", 10),
    ("Economics", "hot", 8),
    ("technology", "hot", 8),
    ("artificial", "hot", 8),
    ("PredictionMarkets", "hot", 15),
]

GOOGLE_NEWS_QUERIES = [
    "Iran US military strike 2026",
    "Federal Reserve interest rate March 2026",
    "AI model benchmark ChatGPT Claude Gemini",
    "Bitcoin price prediction March 2026",
    "Polymarket prediction market",
    "Texas Senate primary election 2026",
    "Somalia US military drone strikes",
    "Switzerland referendum March 2026",
    "US election prediction polls",
]


def fetch_all_news_parallel() -> dict:
    """
    Fetch all news sources in parallel. Returns organized dict.
    Total: 20+ RSS feeds + 12 Reddit subs + CryptoPanic + Google News queries.
    """
    all_items = []
    errors = []

    tasks = []

    # RSS feeds
    for name, (url, max_n) in RSS_FEEDS.items():
        tasks.append(("rss", name, url, max_n))

    # Reddit
    for sub, sort, limit in REDDIT_SUBS:
        tasks.append(("reddit", sub, sort, limit))

    # Google News queries
    for q in GOOGLE_NEWS_QUERIES:
        tasks.append(("gnews", q, None, 8))

    def run_task(task):
        kind = task[0]
        try:
            if kind == "rss":
                _, name, url, max_n = task
                return fetch_rss(url, max_n, name)
            elif kind == "reddit":
                _, sub, sort, limit = task
                return fetch_reddit(sub, sort, limit)
            elif kind == "gnews":
                _, q, _, max_n = task
                return fetch_newsdata_rss(q, max_n)
        except:
            return []
        return []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(run_task, t): t for t in tasks}
        for f in as_completed(futures, timeout=15):
            try:
                items = f.result()
                all_items.extend(items or [])
            except:
                pass

    # CryptoPanic (separate — has its own structure)
    cp_items = fetch_cryptopanic("news", 20)

    # Organize by topic
    organized = {
        "crypto":       [],
        "bitcoin":      [],
        "ai_tech":      [],
        "politics":     [],
        "geopolitics":  [],
        "macro":        [],
        "polymarket":   [],
        "general":      [],
        "raw_cryptopanic": cp_items,
    }

    TOPIC_KW = {
        "bitcoin":     ["bitcoin","btc","satoshi","halving","mstr","microstrategy"],
        "crypto":      ["crypto","ethereum","eth","solana","xrp","defi","nft","stablecoin","binance","coinbase","altcoin","blockchain"],
        "ai_tech":     ["openai","anthropic","claude","gpt","gemini","deepseek","llm","ai model","artificial intelligence","chatbot","nvidia"],
        "politics":    ["trump","senate","congress","election","primary","republican","democrat","white house","supreme court","vote","ballot","texas"],
        "geopolitics": ["iran","russia","ukraine","israel","nato","military","strike","ceasefire","war","diplomacy","sanctions","somalia","pentagon"],
        "macro":       ["fed","federal reserve","interest rate","inflation","recession","gdp","unemployment","tariff","dollar","treasury","fomc","rate cut","rate hike"],
        "polymarket":  ["polymarket","prediction market","odds","kalshi","manifold","metaculus","betting market"],
    }

    for item in all_items:
        title = (item.get("title","") + " " + item.get("desc","")).lower()
        placed = False
        for topic, kws in TOPIC_KW.items():
            if any(kw in title for kw in kws):
                organized[topic].append(item)
                placed = True
                break
        if not placed:
            organized["general"].append(item)

    # Add cryptopanic to crypto
    for cp in cp_items:
        title = cp.get("title","").lower()
        if "bitcoin" in title or "btc" in title:
            organized["bitcoin"].append({"title": cp["title"], "source": cp["source"]})
        else:
            organized["crypto"].append({"title": cp["title"], "source": cp["source"]})

    # Dedup by title similarity within each category
    for cat in organized:
        if cat == "raw_cryptopanic":
            continue
        seen_titles = set()
        deduped = []
        for item in organized[cat]:
            t = item.get("title","").lower()[:60]
            if t not in seen_titles:
                seen_titles.add(t)
                deduped.append(item)
        organized[cat] = deduped

    return organized


def headlines_for_market(question: str, news: dict) -> list[str]:
    """
    Find the most relevant headlines for a specific market question.
    Returns up to 3 relevant headlines.
    Uses domain-specific keyword matching to avoid false positives.
    """
    q_lower = question.lower()

    # Generic stop words — never count these as meaningful matches
    STOP_WORDS = {
        "will","from","that","this","with","have","been","more","than","when",
        "what","which","over","into","their","there","after","about","upon",
        "some","such","most","also","just","even","only","very","much","many",
        "each","both","next","last","same","them","then","they","were","your",
        "make","made","like","time","year","week","days","month","would","could",
        "should","before","during","under","while","post","tweet","tweets","post",
        "february","january","march","april","monday","tuesday","wednesday",
        "thursday","friday","saturday","sunday","2025","2026","2027"
    }

    # Map question patterns to REQUIRED specific keywords
    # Only headlines containing AT LEAST ONE of these will be shown
    TOPIC_KW = {
        "elon musk":      ["elon","musk","twitter","spacex","tesla","doge","x.com","@elonmusk"],
        "bitcoin":        ["bitcoin","btc","crypto","satoshi","microstrategy"],
        "ethereum":       ["ethereum","eth","vitalik"],
        "solana":         ["solana","sol "],
        "iran":           ["iran","tehran","khamenei","irgc","nuclear deal","persian"],
        "israel":         ["israel","idf","netanyahu","gaza","tel aviv","hamas"],
        "ukraine":        ["ukraine","zelensky","kyiv","kyiv","donbas"],
        "russia":         ["russia","putin","kremlin","moscow","russian"],
        "federal reserve":["federal reserve","fomc","powell","rate cut","rate hike","basis points"],
        "trump":          ["trump","white house","maga","executive order","mar-a-lago"],
        "senate":         ["senate","senator","election","primary","ballot","nominee"],
        "crockett":       ["crockett","jasmine","texas senate"],
        "talarico":       ["talarico","james talarico","texas senate"],
        "texas":          ["texas","san antonio","houston","dallas","austin"],
        "somalia":        ["somalia","al-shabaab","mogadishu","africom"],
        "switzerland":    ["switzerland","swiss","zurich","referendum","bern"],
        "openai":         ["openai","chatgpt","gpt-","gpt4","sam altman"],
        "claude":         ["anthropic","claude","sonnet"],
        "gemini":         ["google gemini","google ai","bard"],
        "oscar":          ["oscar","academy award","film award","cinema"],
        "super bowl":     ["super bowl","nfl","halftime","touchdown"],
    }

    # Find required keywords for this question
    required_kws = []
    for key, kws in TOPIC_KW.items():
        if key in q_lower:
            required_kws.extend(kws)

    # Fallback: extract long specific words from the question (7+ chars, not stop words)
    if not required_kws:
        q_specific = [w for w in re.findall(r'\b\w{7,}\b', q_lower) if w not in STOP_WORDS]
        required_kws = q_specific

    if not required_kws:
        return []

    all_headlines = []
    for cat_items in news.values():
        if isinstance(cat_items, list):
            for item in cat_items:
                if isinstance(item, dict):
                    all_headlines.append(item.get("title",""))

    scored = []
    for headline in all_headlines:
        if not headline:
            continue
        h_lower = headline.lower()
        # Must contain at least one required keyword
        kw_hits = sum(1 for kw in required_kws if kw in h_lower)
        if kw_hits >= 1:
            # Bonus for multiple keyword hits
            scored.append((kw_hits, headline))

    scored.sort(key=lambda x: -x[0])
    seen = set()
    results = []
    for _, h in scored:
        h_clean = h[:100]
        if h_clean not in seen:
            seen.add(h_clean)
            results.append(h_clean)
        if len(results) >= 3:
            break
    return results


def format_news_context(question: str, news: dict) -> str:
    """Return formatted news context string for a market question."""
    headlines = headlines_for_market(question, news)
    if not headlines:
        return ""
    lines = []
    for h in headlines[:2]:  # max 2 headlines per pick to keep message compact
        truncated = h[:95] + "…" if len(h) > 95 else h
        lines.append(f"📰 _{truncated}_")
    return "\n   ".join(lines)


def get_polymarket_buzz(news: dict) -> list[str]:
    """Return the hottest Polymarket/prediction market discussions."""
    pm_items = news.get("polymarket", [])
    return [item.get("title","") for item in pm_items[:5] if item.get("title")]


def news_summary(news: dict) -> str:
    """One-paragraph morning summary of key news themes."""
    themes = []
    cats = ["bitcoin", "crypto", "ai_tech", "politics", "geopolitics", "macro"]
    for cat in cats:
        items = news.get(cat, [])
        if items:
            top = items[0].get("title","")
            if top:
                themes.append(f"*{cat.upper()}:* {top[:70]}")
    return "\n".join(themes[:5]) if themes else ""


if __name__ == "__main__":
    import sys
    print("Fetching all news sources...")
    start = datetime.now()
    news = fetch_all_news_parallel()
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nDone in {elapsed:.1f}s\n")
    print("=== NEWS SUMMARY ===")
    print(news_summary(news))
    print(f"\n=== COUNTS ===")
    for cat, items in news.items():
        if cat != "raw_cryptopanic":
            print(f"  {cat}: {len(items)} items")
    print(f"  cryptopanic: {len(news.get('raw_cryptopanic', []))} items")
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(f"\n=== HEADLINES FOR: '{q}' ===")
        ctx = format_news_context(q, news)
        print(ctx if ctx else "(no matches)")
