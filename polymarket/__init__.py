"""
Polymarket Prediction Market Engine v2.0
Modular, scalable, learning-capable.

Modules:
  config      — constants, sizing, keywords, fees
  fetcher     — all external API calls
  resolution  — resolution rule parsing + classification
  scorer      — market scoring engine
  portfolio   — portfolio state management
  performance — pick tracking + edge analysis
  formatters  — Telegram output formatting
  news/       — news intelligence (RSS, Reddit, CryptoPanic)
  models/     — predictive models (tweet count, etc.)
  main        — orchestrator (morning_briefing, evening_review)
"""

__version__ = "2.0.0"

from .main import morning_briefing, evening_review, portfolio_snapshot
