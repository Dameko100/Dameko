"""
News fetcher: pulls articles from RSS feeds and NewsAPI.
Covers finance, technology, politics, wars, AI, crypto, and general world events.
"""

import feedparser
import requests
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RSS feed sources grouped by category
# ---------------------------------------------------------------------------
RSS_FEEDS: Dict[str, List[str]] = {
    "finance": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.ft.com/?format=rss",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    ],
    "technology": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://feeds.feedburner.com/TheHackersNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ],
    "politics": [
        "https://feeds.reuters.com/reuters/politicsNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://thehill.com/rss/syndicator/19110",
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "wars_conflicts": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.defensenews.com/rss/",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "ai": [
        "https://venturebeat.com/category/ai/feed/",
        "https://feeds.feedburner.com/AITrends",
        "https://www.artificialintelligence-news.com/feed/",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ],
    "general": [
        "https://feeds.reuters.com/reuters/topNews",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://www.theguardian.com/world/rss",
    ],
}


class Article:
    """Represents a news article."""

    def __init__(
        self,
        title: str,
        url: str,
        summary: str,
        source: str,
        category: str,
        published_at: Optional[datetime] = None,
    ):
        self.title = title
        self.url = url
        self.summary = summary
        self.source = source
        self.category = category
        self.published_at = published_at or datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Article [{self.category}] {self.title[:60]}>"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "category": self.category,
            "published_at": self.published_at.isoformat(),
        }


class NewsFetcher:
    """Fetches news articles from RSS feeds and NewsAPI."""

    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "DamekoNewsBot/1.0 (news aggregator)"}
        )

    # ------------------------------------------------------------------
    # RSS
    # ------------------------------------------------------------------

    def fetch_rss_feed(self, url: str, category: str) -> List[Article]:
        """Parse a single RSS feed and return a list of Articles."""
        articles: List[Article] = []
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "DamekoNewsBot/1.0"})
            source = feed.feed.get("title", url)

            for entry in feed.entries[:15]:  # cap to 15 most recent per feed
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Strip HTML tags from summary
                import re
                summary = re.sub(r"<[^>]+>", "", summary)[:400]

                if not title or not link:
                    continue

                # Parse published date
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                articles.append(
                    Article(
                        title=title,
                        url=link,
                        summary=summary,
                        source=source,
                        category=category,
                        published_at=published_at,
                    )
                )
        except Exception as e:
            logger.warning(f"Error fetching RSS feed {url}: {e}")

        return articles

    def fetch_all_rss(self) -> List[Article]:
        """Fetch all configured RSS feeds and return combined list."""
        all_articles: List[Article] = []
        for category, urls in RSS_FEEDS.items():
            for url in urls:
                articles = self.fetch_rss_feed(url, category)
                all_articles.extend(articles)
                logger.debug(f"Fetched {len(articles)} articles from {url}")
        return all_articles

    # ------------------------------------------------------------------
    # NewsAPI
    # ------------------------------------------------------------------

    NEWSAPI_TOPICS = [
        "war OR conflict OR military",
        "artificial intelligence OR AI technology",
        "election OR politics OR government",
        "economy OR inflation OR recession OR stocks",
        "cryptocurrency OR bitcoin OR ethereum",
        "geopolitics OR sanctions OR diplomacy",
        "climate OR disaster OR earthquake",
        "sports championship OR world cup OR olympics",
    ]

    def fetch_newsapi(self, query: Optional[str] = None) -> List[Article]:
        """Fetch top headlines and topic searches from NewsAPI."""
        if not self.newsapi_key:
            return []

        articles: List[Article] = []
        base_url = "https://newsapi.org/v2"
        headers = {"X-Api-Key": self.newsapi_key}

        # Top headlines
        try:
            resp = self.session.get(
                f"{base_url}/top-headlines",
                params={"language": "en", "pageSize": 30},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            for item in resp.json().get("articles", []):
                articles.append(self._newsapi_item_to_article(item, "general"))
        except Exception as e:
            logger.warning(f"NewsAPI top-headlines error: {e}")

        # Topic searches
        topics = [query] if query else self.NEWSAPI_TOPICS
        for topic in topics[:4]:  # limit API calls
            try:
                resp = self.session.get(
                    f"{base_url}/everything",
                    params={
                        "q": topic,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 10,
                    },
                    headers=headers,
                    timeout=10,
                )
                resp.raise_for_status()
                category = self._infer_category(topic)
                for item in resp.json().get("articles", []):
                    articles.append(self._newsapi_item_to_article(item, category))
            except Exception as e:
                logger.warning(f"NewsAPI search error for '{topic}': {e}")

        return articles

    def _newsapi_item_to_article(self, item: dict, category: str) -> Article:
        published_at = None
        if item.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    item["publishedAt"].replace("Z", "+00:00")
                )
            except Exception:
                pass
        return Article(
            title=item.get("title", "").strip(),
            url=item.get("url", "").strip(),
            summary=(item.get("description") or "")[:400],
            source=item.get("source", {}).get("name", "NewsAPI"),
            category=category,
            published_at=published_at,
        )

    def _infer_category(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["war", "conflict", "military"]):
            return "wars_conflicts"
        if any(k in q for k in ["ai", "artificial intelligence"]):
            return "ai"
        if any(k in q for k in ["election", "politics", "government"]):
            return "politics"
        if any(k in q for k in ["economy", "inflation", "stocks", "recession"]):
            return "finance"
        if any(k in q for k in ["crypto", "bitcoin", "ethereum"]):
            return "crypto"
        return "world"

    # ------------------------------------------------------------------
    # Combined fetch
    # ------------------------------------------------------------------

    def fetch_all(self) -> List[Article]:
        """Fetch from all sources and return deduplicated articles."""
        articles = self.fetch_all_rss()
        articles += self.fetch_newsapi()

        # Deduplicate by URL
        seen_urls: set = set()
        unique: List[Article] = []
        for a in articles:
            if a.url and a.url not in seen_urls:
                seen_urls.add(a.url)
                unique.append(a)

        logger.info(f"Fetched {len(unique)} unique articles total")
        return unique
