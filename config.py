"""
Configuration loaded from environment variables / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Telegram ----
    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

    # ---- NewsAPI (optional but recommended) ----
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

    # ---- Scheduler ----
    # How often to poll news feeds (minutes)
    POLL_INTERVAL_MINUTES: int = int(os.getenv("POLL_INTERVAL_MINUTES", "10"))

    # Hour (UTC, 0-23) to send daily trending-markets digest
    DIGEST_HOUR_UTC: int = int(os.getenv("DIGEST_HOUR_UTC", "8"))

    # ---- Filtering ----
    # Minimum importance score to trigger a notification (0.0 - 1.0)
    MIN_IMPORTANCE_SCORE: float = float(os.getenv("MIN_IMPORTANCE_SCORE", "0.2"))

    # Minimum Polymarket liquidity to include a market in alerts ($)
    MIN_MARKET_LIQUIDITY: float = float(os.getenv("MIN_MARKET_LIQUIDITY", "100"))

    # Maximum markets shown per article
    MAX_MARKETS_PER_ALERT: int = int(os.getenv("MAX_MARKETS_PER_ALERT", "4"))

    # ---- Storage ----
    # Days to keep seen-article records before cleanup
    SEEN_ARTICLES_TTL_DAYS: int = int(os.getenv("SEEN_ARTICLES_TTL_DAYS", "7"))
