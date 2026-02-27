# Polymarket Algorithm — Lessons Learned

## Day 1 (Feb 27, 2026) — Mistakes & Fixes

---

### ❌ MISTAKE 1: Recommended intraday bet without checking live data first
**What happened:** Recommended Elon 300-319 tweets YES at 0.755 as part of "final picks" without first checking xtracker for the live count. I told Jacobo to check xtracker, then included the bet anyway without waiting.
**Impact:** Position dropped from 0.755 to 0.53 (-28%) as market priced in uncertainty.
**Fix:** For ANY market resolving within 24h with a live tracker/data source — CHECK THE SOURCE FIRST before recommending. Never include intraday markets in final picks without live verification.
**Rule added:** `if market.endDate == today and market.hasLiveTracker: check_live_data_first()`

---

### ❌ MISTAKE 2: Cited outdated news headline as market edge (Crockett)
**What happened:** News scraper returned headline "Crockett leads Talarico by double digits" — I assumed this meant the market (29% Crockett) was undervalued. In reality, the multi-candidate market showed Talarico at 72% with $1.9M volume and +32% in 7 days. Smart money had already moved.
**Impact:** Almost sent Jacobo into a likely losing bet.
**Fix:** For multi-candidate political markets — ALWAYS check the full multi-outcome market page, not just the binary YES/NO for one candidate. High-volume markets (>$500K) with strong directional momentum are more reliable than individual poll headlines.
**Rule added:** `if market.type == 'political_primary': check_full_multicandidate_market() before citing polls`

---

### ❌ MISTAKE 3: BTC intraday range bets — resolution rules not surfaced upfront
**What happened:** Recommended BTC $64-66K range bets without clearly explaining they resolve on a SINGLE 1-minute Binance candle at noon ET — not end of day.
**Impact:** Jacobo nearly bet thinking it was an end-of-day resolution. Different risk profile entirely.
**Fix:** Read resolution rules for EVERY pick before finalizing. If resolution is a single price point (not a range over time), flag it prominently: ⚠️ SINGLE CANDLE RESOLUTION.
**Rule added:** `if 'close' in resolution_rules and '12:00' in resolution_rules: flag_as_precision_bet()`

---

### ❌ MISTAKE 4: News matching algorithm returned irrelevant headlines
**What happened:** Bitcoin price prediction and mortgage rate articles were linked to Elon Musk tweet count markets. Pure word overlap matching without relevance filters.
**Impact:** Lost credibility, bad UX.
**Fix:** Rewrote news matching to use domain-specific required keywords + stop word filtering. Deployed Feb 27.
**Status:** ✅ FIXED

---

### ❌ MISTAKE 5: Flip-flopped on Elon bet advice
**What happened:** Said "hold" → then "mathematically selling is better" → then "hold" again. Confused Jacobo.
**Impact:** Bad UX, lost trust.
**Fix:** Make a call and stick with it unless the data changes significantly. If flip-flopping, explain exactly what changed and why. Show the math upfront.
**Rule added:** Only change recommendation if NEW DATA arrives (not just market price movement alone).

---

### ❌ MISTAKE 6: Wrong Crockett market initially recommended
**What happened:** Jacobo bought "Crockett wins primary AND loses general" (Nov 2026) instead of "Crockett wins primary" (March 3). Both existed, the slugs were similar.
**Impact:** Jacobo had to sell at a loss (-$1.30).
**Fix:** Always verify the exact market title and end date before sending the link. For political markets, multiple versions often exist with very different resolution criteria.
**Rule added:** `verify_market_title_and_enddate() before sending any link`

---

## Algorithm Improvement Roadmap

### PRIORITY 1 — Pre-bet checklist (implement before next morning run)
- [ ] For markets ending TODAY: auto-fetch live tracker data before scoring
- [ ] For political primary markets: fetch full multi-candidate market, not just binary
- [ ] For all picks: surface resolution rules summary in 1 sentence
- [ ] Add "resolution type" field: END_OF_DAY | SINGLE_CANDLE | EVENT | TRACKER

### PRIORITY 2 — Scoring improvements
- [ ] Penalize markets with SINGLE_CANDLE resolution (higher variance, harder to edge)
- [ ] Penalize markets where momentum contradicts our bet direction
- [ ] Add "market version check" — if multiple markets exist for same event, pick the right one
- [ ] Volume-weighted consensus check: if >$500K volume disagrees with our pick, flag it

### PRIORITY 3 — News intelligence
- [ ] Check publication DATE of headlines — reject anything >72h old for intraday markets
- [ ] For political markets: weight prediction market prices > individual polls
- [ ] Cross-reference multiple sources before calling a market "undervalued"

---

## Golden Rules (always apply)

1. **Read the resolution rules. Every time. No exceptions.**
2. **Check live data for anything resolving today.**
3. **High-volume markets (>$500K) price in more info than any single news headline.**
4. **When in doubt, skip the bet. Cash is a position.**
5. **Never flip-flop without new data.**
6. **Verify the exact market link before sending — title, end date, resolution criteria.**
