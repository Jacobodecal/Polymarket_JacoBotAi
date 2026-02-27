#!/usr/bin/env python3
"""
Elon Musk Tweet Count Estimator
Uses hourly activity weights instead of flat daily average.

Key insight (Jacobo, Feb 27 2026):
  - Flat avg/day is naive — Elon sleeps and has burst periods
  - Weight remaining hours by historical activity at those hours
  - Gives much more accurate projection of final tweet count

Data source: xtracker.polymarket.com (screenshots) + known behavior patterns
"""

from datetime import datetime, timezone, timedelta

# ── Hourly activity weights (ET timezone) ─────────────────────────────────────
# Based on Elon's known posting behavior:
#   - Very active: 8-11AM ET (morning burst), 7-11PM ET (evening/night)
#   - Moderately active: 11AM-3PM ET, 3-7PM ET
#   - Low: 12AM-3AM ET, 6-8AM ET
#   - Near zero: 3-6AM ET (asleep)
#
# Weights are relative — will be normalized.
# Source: general knowledge + xtracker pattern analysis from screenshots.
# Update these weights as we collect more data from Jacobo's screenshots.

ELON_HOURLY_WEIGHTS_ET = {
    0:  0.6,   # midnight — still active sometimes
    1:  0.4,
    2:  0.2,
    3:  0.05,  # asleep
    4:  0.05,  # asleep
    5:  0.1,
    6:  0.3,
    7:  0.7,
    8:  1.2,   # morning burst starts
    9:  1.5,   # peak morning
    10: 1.4,
    11: 1.2,
    12: 1.0,   # midday
    13: 0.9,
    14: 0.8,
    15: 0.9,
    16: 1.0,
    17: 1.1,
    18: 1.2,
    19: 1.3,   # evening ramp
    20: 1.4,
    21: 1.5,   # evening peak
    22: 1.3,
    23: 0.9,
}

# Total weight across all 24 hours
TOTAL_WEIGHT = sum(ELON_HOURLY_WEIGHTS_ET.values())


def expected_posts_in_window(
    current_count: int,
    daily_avg: float,
    window_start_et: datetime,
    window_end_et: datetime,
    resolution_end_et: datetime,
) -> dict:
    """
    Estimate expected additional posts from now until resolution.

    Args:
        current_count: Posts counted so far in this period
        daily_avg: Average posts per day (from xtracker)
        window_start_et: When the tracking period started (ET)
        window_end_et: When the tracking period ends / resolves (ET)
        resolution_end_et: Same as window_end_et in most cases

    Returns:
        dict with expected_additional, expected_final, posts_per_active_hour, risk_assessment
    """
    now_et = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5)))

    # Weight of hours already elapsed (what we've "used" of the daily budget)
    elapsed_weight = 0.0
    remaining_weight = 0.0

    hour = window_start_et.replace(minute=0, second=0, microsecond=0)
    while hour < window_end_et:
        h = hour.hour
        w = ELON_HOURLY_WEIGHTS_ET.get(h, 0.5)
        if hour < now_et:
            elapsed_weight += w
        else:
            remaining_weight += w
        hour += timedelta(hours=1)

    total_period_weight = elapsed_weight + remaining_weight
    if total_period_weight == 0:
        return {"error": "zero weight window"}

    # Expected posts in remaining window based on hourly distribution
    # Scale: if 307 posts happened in elapsed_weight worth of hours,
    # the remaining_weight fraction of the day would produce proportionally
    posts_per_weight_unit = current_count / elapsed_weight if elapsed_weight > 0 else (daily_avg / TOTAL_WEIGHT)
    expected_additional = posts_per_weight_unit * remaining_weight

    # Alternative: use daily_avg to set the scale
    expected_additional_avg = daily_avg * (remaining_weight / TOTAL_WEIGHT)

    # Blend: use actual pace from current data (more reliable if we have good count)
    blend = 0.7 if elapsed_weight > 8 else 0.4  # trust actual data more as period progresses
    expected_additional_blended = blend * expected_additional + (1 - blend) * expected_additional_avg

    expected_final = current_count + expected_additional_blended

    # Risk: how many posts to bust each range boundary
    # (caller provides the range max)
    return {
        "current": current_count,
        "expected_additional": round(expected_additional_blended, 1),
        "expected_final": round(expected_final, 1),
        "remaining_weight": round(remaining_weight, 2),
        "elapsed_weight": round(elapsed_weight, 2),
        "posts_per_weight_unit": round(posts_per_weight_unit, 2),
        "remaining_hours": round((window_end_et - now_et).total_seconds() / 3600, 2),
        "note": "Weighted by hourly activity — sleep hours count less"
    }


def analyze_elon_market(
    current_count: int,
    daily_avg: float = 44,
    range_min: int = 300,
    range_max: int = 319,
    resolution_iso: str = "2026-02-27T17:00:00+00:00",
    period_start_iso: str = "2026-02-20T17:00:00+00:00",
) -> str:
    """Full analysis for an Elon tweet count market."""
    ET = timezone(timedelta(hours=-5))
    res_end = datetime.fromisoformat(resolution_iso).astimezone(ET)
    period_start = datetime.fromisoformat(period_start_iso).astimezone(ET)

    result = expected_posts_in_window(
        current_count=current_count,
        daily_avg=daily_avg,
        window_start_et=period_start,
        window_end_et=res_end,
        resolution_end_et=res_end,
    )

    now_et = datetime.now(timezone.utc).astimezone(ET)
    expected_final = result["expected_final"]
    to_bust_top = range_max + 1 - current_count
    to_bust_bottom = current_count - range_min  # how far above minimum

    in_range = range_min <= expected_final <= range_max
    above_range = expected_final > range_max
    below_range = expected_final < range_min

    lines = [
        f"📊 ELON TWEET ANALYSIS — {now_et.strftime('%H:%M ET')}",
        f"Current count: {current_count} | Range: {range_min}-{range_max} | Resolves: {res_end.strftime('%H:%M ET')}",
        f"Remaining: {result['remaining_hours']:.1f}h | Active hours weight: {result['remaining_weight']:.1f} (of {result['elapsed_weight']+result['remaining_weight']:.1f} total)",
        f"Expected additional posts (weighted): +{result['expected_additional']} → Final: ~{expected_final}",
        "",
    ]

    if in_range:
        margin_top = range_max + 1 - expected_final
        lines.append(f"✅ PROJECTED IN RANGE — {margin_top:.0f} post margin to bust top")
    elif above_range:
        lines.append(f"❌ PROJECTED ABOVE RANGE — already trending to {expected_final:.0f}")
    else:
        lines.append(f"❌ PROJECTED BELOW RANGE — {expected_final:.0f} < {range_min}")

    lines.append(f"Posts needed to bust ceiling ({range_max+1}): {to_bust_top} more in {result['remaining_hours']:.1f}h")
    lines.append(f"= {to_bust_top/result['remaining_hours']:.1f} posts/hour needed to bust (weighted avg remaining: {result['posts_per_weight_unit']*ELON_HOURLY_WEIGHTS_ET.get(now_et.hour,1.0):.1f}/h this hour)")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 307
    print(analyze_elon_market(
        current_count=count,
        daily_avg=44,
        range_min=300,
        range_max=319,
        resolution_iso="2026-02-27T17:00:00+00:00",
        period_start_iso="2026-02-20T17:00:00+00:00",
    ))
