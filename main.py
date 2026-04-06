"""
Dameko News Bot - Main entry point.

Runs a polling loop that:
  1. Fetches news from RSS feeds + NewsAPI every N minutes.
  2. Scores each article for Polymarket relevance.
  3. Searches Polymarket for related markets.
  4. Sends a Telegram alert with the article and market links.
  5. Sends a daily digest of top trending Polymarket markets.

Usage:
    python main.py

Environment variables (see .env.example):
    TELEGRAM_BOT_TOKEN   - required
    TELEGRAM_CHAT_ID     - required
    NEWSAPI_KEY          - optional (broadens news coverage)
"""

import logging
import time
import schedule
from datetime import datetime, timezone

from config import Config
from src.news_fetcher import NewsFetcher, Article
from src.polymarket import PolymarketClient
from src.telegram_notifier import TelegramNotifier
from src.matcher import ArticleMatcher, score_article_importance
from src.storage import ArticleStore

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dameko")

# ---------------------------------------------------------------------------
# Component initialisation
# ---------------------------------------------------------------------------
cfg = Config()
fetcher = NewsFetcher(newsapi_key=cfg.NEWSAPI_KEY or None)
poly = PolymarketClient()
notifier = TelegramNotifier(cfg.TELEGRAM_BOT_TOKEN, cfg.TELEGRAM_CHAT_ID)
matcher = ArticleMatcher()
store = ArticleStore()


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def process_article(article: Article) -> None:
    """Run the full pipeline for a single article."""
    if not article.url or not article.title:
        return

    # Skip already-seen articles
    if store.is_seen(article.url):
        return

    # Score the article
    score = score_article_importance(article)
    if score < cfg.MIN_IMPORTANCE_SCORE:
        store.mark_seen(article.url, article.title, article.category)
        return

    logger.info(f"[{article.category}] Processing: {article.title[:70]} (score={score:.2f})")

    # Find related Polymarket markets
    queries = matcher.get_queries(article, max_queries=4)
    markets = poly.search_markets_multi(
        queries,
        limit_per_query=3,
        min_liquidity=cfg.MIN_MARKET_LIQUIDITY,
    )
    markets = markets[: cfg.MAX_MARKETS_PER_ALERT]

    logger.info(f"  -> Found {len(markets)} markets for queries: {queries}")

    # Send Telegram notification
    success = notifier.send_news_alert(article, markets)

    # Persist
    store.mark_seen(article.url, article.title, article.category)
    store.log_notification(article.url, article.title, len(markets), success)

    if success:
        logger.info(f"  -> Alert sent ✓ ({len(markets)} markets)")
    else:
        logger.warning(f"  -> Alert failed ✗")


def poll_news() -> None:
    """Fetch all news and process new articles. Called on schedule."""
    logger.info("--- Polling news sources ---")
    try:
        articles = fetcher.fetch_all()
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return

    new_count = 0
    for article in articles:
        if not store.is_seen(article.url):
            new_count += 1

    logger.info(f"Found {len(articles)} articles, {new_count} new")

    for article in articles:
        try:
            process_article(article)
            time.sleep(0.5)  # be polite to Telegram rate limits
        except Exception as e:
            logger.error(f"Error processing article '{article.title[:50]}': {e}")

    # Weekly cleanup
    store.cleanup_old_records(days=cfg.SEEN_ARTICLES_TTL_DAYS)


def send_daily_digest() -> None:
    """Send a digest of top Polymarket markets. Called once daily."""
    logger.info("--- Sending daily digest ---")
    try:
        markets = poly.get_trending_markets(limit=10)
        if markets:
            notifier.send_digest(markets, title="Mercados Trending del Día 🔥")
            logger.info(f"Daily digest sent with {len(markets)} markets")
        else:
            logger.warning("No trending markets found for digest")
    except Exception as e:
        logger.error(f"Daily digest error: {e}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting Dameko News Bot...")

    # Verify Telegram connection
    if not notifier.test_connection():
        raise SystemExit("❌ Telegram connection failed. Check TELEGRAM_BOT_TOKEN.")

    # Send startup message
    notifier.send_startup_message()

    # Log initial DB stats
    stats = store.stats()
    logger.info(f"DB stats: {stats}")

    # Schedule polling
    schedule.every(cfg.POLL_INTERVAL_MINUTES).minutes.do(poll_news)
    logger.info(f"News polling scheduled every {cfg.POLL_INTERVAL_MINUTES} minutes")

    # Schedule daily digest
    digest_time = f"{cfg.DIGEST_HOUR_UTC:02d}:00"
    schedule.every().day.at(digest_time).do(send_daily_digest)
    logger.info(f"Daily digest scheduled at {digest_time} UTC")

    # Run immediately on startup
    poll_news()

    # Main loop
    logger.info("Bot running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
