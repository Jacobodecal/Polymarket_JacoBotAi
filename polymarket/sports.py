"""
Polymarket — Sports Intelligence Module
Fetches form, standings, and generates value scores vs market odds.
Free APIs only: TheSportsDB, API-Football (free tier), open esports sources.

Scalable: add new leagues/competitions by extending LEAGUE_IDS.
"""

import requests, json, re
from datetime import datetime, timezone
from typing import Optional

TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PolyBot/2.0)"}
SPORTSDB = "https://www.thesportsdb.com/api/v1/json/3"

# ── League IDs (TheSportsDB) ──────────────────────────────────────────────────
LEAGUE_IDS = {
    # Football
    "EPL":          4328,
    "LA_LIGA":      4335,
    "BUNDESLIGA":   4331,
    "SERIE_A":      4332,
    "LIGUE_1":      4334,
    "CHAMPIONS_LEAGUE": 4480,
    "COPA_DEL_REY": 4400,
    "FA_CUP":       4337,
    # US Sports
    "NBA":          4387,
    "NFL":          4391,
    "MLB":          4424,
    "NHL":          4380,
    # Brazil
    "BRASILEIRAO":  4351,
}

# ── Team Data ─────────────────────────────────────────────────────────────────

def search_team(name: str) -> Optional[dict]:
    """Search for a team by name. Returns first match or None."""
    try:
        r = requests.get(f"{SPORTSDB}/searchteams.php",
                         params={"t": name}, headers=HEADERS, timeout=TIMEOUT)
        teams = r.json().get("teams") or []
        return teams[0] if teams else None
    except Exception:
        return None


def get_team_last_results(team_id: str, n: int = 5) -> list[dict]:
    """Get last N results for a team."""
    try:
        r = requests.get(f"{SPORTSDB}/eventslast.php",
                         params={"id": team_id}, headers=HEADERS, timeout=TIMEOUT)
        results = r.json().get("results") or []
        return results[-n:] if len(results) >= n else results
    except Exception:
        return []


def get_team_next_events(team_id: str, n: int = 3) -> list[dict]:
    """Get next N scheduled events for a team."""
    try:
        r = requests.get(f"{SPORTSDB}/eventsnext.php",
                         params={"id": team_id}, headers=HEADERS, timeout=TIMEOUT)
        events = r.json().get("events") or []
        return events[:n]
    except Exception:
        return []


def get_league_table(league_id: int, season: str = "2025-2026") -> list[dict]:
    """Get league standings."""
    try:
        r = requests.get(f"{SPORTSDB}/lookuptable.php",
                         params={"l": league_id, "s": season},
                         headers=HEADERS, timeout=TIMEOUT)
        return r.json().get("table") or []
    except Exception:
        return []


# ── Form Calculator ────────────────────────────────────────────────────────────

def compute_form(results: list[dict], team_name: str) -> dict:
    """
    Compute recent form from last N results.
    Returns: {wins, draws, losses, form_string, pts_per_game, goals_for, goals_against}
    """
    wins = draws = losses = gf = ga = 0
    form_chars = []

    for e in results:
        home = e.get("strHomeTeam", "")
        away = e.get("strAwayTeam", "")
        hs = e.get("intHomeScore")
        as_ = e.get("intAwayScore")
        if hs is None or as_ is None:
            continue
        hs, as_ = int(hs), int(as_)
        is_home = team_name.lower() in home.lower()
        team_score = hs if is_home else as_
        opp_score  = as_ if is_home else hs
        gf += team_score; ga += opp_score
        if team_score > opp_score:
            wins += 1; form_chars.append("W")
        elif team_score == opp_score:
            draws += 1; form_chars.append("D")
        else:
            losses += 1; form_chars.append("L")

    total = wins + draws + losses
    ppg = (wins * 3 + draws) / total if total > 0 else 0

    return {
        "wins": wins, "draws": draws, "losses": losses,
        "form": "".join(form_chars),
        "pts_per_game": round(ppg, 2),
        "goals_for": gf, "goals_against": ga,
        "games": total,
    }


# ── Value Analysis ─────────────────────────────────────────────────────────────

def form_to_win_probability(form_home: dict, form_away: dict,
                             is_home_team: bool) -> float:
    """
    Rough win probability estimate based on form stats.
    Home advantage adds ~5%.
    """
    ppg_home = form_home.get("pts_per_game", 1.5)
    ppg_away = form_away.get("pts_per_game", 1.5)
    total = ppg_home + ppg_away
    if total == 0:
        return 0.5
    base_prob = ppg_home / total
    home_bonus = 0.05 if is_home_team else -0.05
    return min(max(base_prob + home_bonus, 0.1), 0.9)


def analyze_match(home_team: str, away_team: str,
                  market_yes_price: float, league_id: int = None) -> dict:
    """
    Full match analysis. Returns value signal vs market price.
    home_team = team that resolves YES if they win.
    market_yes_price = Polymarket YES price.
    """
    home = search_team(home_team)
    away = search_team(away_team)

    if not home or not away:
        return {"error": f"Team not found: {home_team if not home else away_team}"}

    home_results = get_team_last_results(home["idTeam"], 5)
    away_results = get_team_last_results(away["idTeam"], 5)

    home_form = compute_form(home_results, home_team)
    away_form = compute_form(away_results, away_team)

    # League table position (if league provided)
    home_rank = away_rank = None
    if league_id:
        table = get_league_table(league_id)
        for row in table:
            name = row.get("strTeam", "")
            if home_team.lower() in name.lower():
                home_rank = int(row.get("intRank", 99))
            if away_team.lower() in name.lower():
                away_rank = int(row.get("intRank", 99))

    # Form-based win probability
    form_prob = form_to_win_probability(home_form, away_form, is_home_team=True)

    # Rank adjustment (better rank = more likely to win)
    rank_adj = 0.0
    if home_rank and away_rank:
        rank_diff = away_rank - home_rank  # positive if home is higher
        rank_adj = min(rank_diff * 0.01, 0.15)  # max ±15%
    adj_prob = min(max(form_prob + rank_adj, 0.1), 0.9)

    # Value vs market
    market_implied = market_yes_price
    edge = adj_prob - market_implied
    value_signal = "OVERPRICED_YES" if edge < -0.08 else \
                   "UNDERPRICED_YES" if edge > 0.08 else "FAIR"

    return {
        "home_team":      home_team,
        "away_team":      away_team,
        "home_form":      home_form,
        "away_form":      away_form,
        "home_rank":      home_rank,
        "away_rank":      away_rank,
        "form_win_prob":  round(form_prob, 3),
        "adjusted_prob":  round(adj_prob, 3),
        "market_price":   market_implied,
        "edge":           round(edge, 3),
        "value_signal":   value_signal,
        "recommendation": _recommend(edge, adj_prob, market_yes_price),
    }


def _recommend(edge: float, our_prob: float, market_price: float) -> str:
    if edge > 0.10:
        return f"BUY YES — we estimate {our_prob*100:.0f}% vs market {market_price*100:.0f}%"
    if edge < -0.10:
        no_prob = 1 - our_prob
        no_price = 1 - market_price
        return f"BUY NO — we estimate {no_prob*100:.0f}% NO vs market {no_price*100:.0f}% NO"
    return "SKIP — market fairly priced, no clear edge"


def format_match_analysis(analysis: dict) -> str:
    """Format match analysis for Telegram output."""
    if "error" in analysis:
        return f"⚠️ {analysis['error']}"

    hf = analysis["home_form"]
    af = analysis["away_form"]
    lines = [
        f"*{analysis['home_team']}* (home) vs *{analysis['away_team']}* (away)",
        f"Form: {analysis['home_team'].split()[0]}: `{hf['form']}` ({hf['pts_per_game']} PPG) | "
        f"{analysis['away_team'].split()[0]}: `{af['form']}` ({af['pts_per_game']} PPG)",
    ]
    if analysis["home_rank"] and analysis["away_rank"]:
        lines.append(f"Rank: #{analysis['home_rank']} vs #{analysis['away_rank']}")

    lines += [
        f"Our estimate: *{analysis['adjusted_prob']*100:.0f}%* YES | Market: *{analysis['market_price']*100:.0f}%* YES",
        f"Edge: {analysis['edge']*100:+.1f}% → **{analysis['recommendation']}**",
    ]
    return "\n".join(lines)
