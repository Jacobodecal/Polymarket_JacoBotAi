#!/usr/bin/env python3
"""
polymarket_scout.py — Entry point (thin wrapper)
All logic lives in the polymarket/ package.

Usage:
  python3 polymarket_scout.py --mode morning
  python3 polymarket_scout.py --mode evening
  python3 polymarket_scout.py --mode portfolio
"""

import argparse, sys
from pathlib import Path

# Ensure scripts dir is in path
sys.path.insert(0, str(Path(__file__).parent))

from polymarket import morning_briefing, evening_review, portfolio_snapshot


def main():
    ap = argparse.ArgumentParser(description="Polymarket Pick Engine v2")
    ap.add_argument("--mode", choices=["morning", "evening", "portfolio"], default="morning")
    ap.add_argument("--budget", type=float, default=100.0, help="Daily budget override")
    ap.add_argument("--days",   type=int,   default=30,   help="Max days ahead to scan")
    args = ap.parse_args()

    if args.mode == "morning":
        print(morning_briefing(daily_budget=args.budget, days_max=args.days))
    elif args.mode == "evening":
        print(evening_review(days_max=args.days))
    elif args.mode == "portfolio":
        print(portfolio_snapshot())


if __name__ == "__main__":
    main()
