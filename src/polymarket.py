"""
Polymarket API client.
Uses the public Gamma API to search for active prediction markets
that match keywords extracted from news articles.
"""

import requests
import logging
from typing import List, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
POLYMARKET_BASE = "https://polymarket.com/event"


class Market:
    """Represents a Polymarket prediction market."""

    def __init__(self, data: dict):
        self.id: str = str(data.get("id", ""))
        self.question: str = data.get("question", "")
        self.slug: str = data.get("slug", "")
        self.end_date: Optional[str] = data.get("endDate")
        self.active: bool = data.get("active", False)
        self.closed: bool = data.get("closed", False)
        self.volume: float = float(data.get("volume", 0) or 0)
        self.liquidity: float = float(data.get("liquidity", 0) or 0)
        self.description: str = (data.get("description") or "")[:300]

        # Outcomes / prices
        self.outcomes: List[str] = []
        self.prices: List[float] = []
        try:
            import json
            outcomes_raw = data.get("outcomes", "[]")
            prices_raw = data.get("outcomePrices", "[]")
            if isinstance(outcomes_raw, str):
                self.outcomes = json.loads(outcomes_raw)
            elif isinstance(outcomes_raw, list):
                self.outcomes = outcomes_raw
            if isinstance(prices_raw, str):
                self.prices = [float(p) for p in json.loads(prices_raw)]
            elif isinstance(prices_raw, list):
                self.prices = [float(p) for p in prices_raw]
        except Exception:
            pass

        # Event-level slug (used for URL)
        self.event_slug: str = data.get("groupItemTitle", self.slug) or self.slug
        self.condition_id: str = data.get("conditionId", "")

    @property
    def url(self) -> str:
        if self.slug:
            return f"https://polymarket.com/event/{self.slug}"
        return "https://polymarket.com"

    @property
    def odds_summary(self) -> str:
        """Human readable odds like 'Yes: 72% / No: 28%'"""
        if self.outcomes and self.prices and len(self.outcomes) == len(self.prices):
            parts = []
            for outcome, price in zip(self.outcomes, self.prices):
                pct = round(price * 100, 1)
                parts.append(f"{outcome}: {pct}%")
            return " / ".join(parts)
        return ""

    def __repr__(self) -> str:
        return f"<Market {self.question[:60]}>"


class PolymarketClient:
    """Client for the Polymarket Gamma public API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DamekoNewsBot/1.0"})

    def search_markets(
        self,
        query: str,
        limit: int = 5,
        min_liquidity: float = 100.0,
    ) -> List[Market]:
        """
        Search active markets by keyword query.
        Returns markets sorted by volume descending.
        """
        if not query.strip():
            return []

        markets: List[Market] = []
        try:
            params = {
                "limit": min(limit * 3, 30),  # fetch extra to filter
                "active": "true",
                "closed": "false",
                "search": query,
            }
            resp = self.session.get(
                f"{GAMMA_API_BASE}/markets",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # Gamma API may return list directly or wrapped
            items = data if isinstance(data, list) else data.get("markets", data.get("data", []))

            for item in items:
                m = Market(item)
                if not m.active or m.closed:
                    continue
                if m.liquidity < min_liquidity:
                    continue
                markets.append(m)

            # Sort by volume
            markets.sort(key=lambda m: m.volume, reverse=True)
            markets = markets[:limit]

        except requests.exceptions.RequestException as e:
            logger.warning(f"Polymarket API error for query '{query}': {e}")
        except Exception as e:
            logger.warning(f"Unexpected error querying Polymarket for '{query}': {e}")

        return markets

    def search_markets_multi(
        self,
        queries: List[str],
        limit_per_query: int = 3,
        min_liquidity: float = 100.0,
    ) -> List[Market]:
        """
        Search multiple queries and deduplicate by market ID.
        Returns the best matching markets overall.
        """
        seen_ids: set = set()
        all_markets: List[Market] = []

        for query in queries:
            results = self.search_markets(query, limit=limit_per_query, min_liquidity=min_liquidity)
            for m in results:
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    all_markets.append(m)

        # Final sort by volume
        all_markets.sort(key=lambda m: m.volume, reverse=True)
        return all_markets

    def get_trending_markets(self, limit: int = 10) -> List[Market]:
        """Fetch top active markets by volume (used for daily digest)."""
        markets: List[Market] = []
        try:
            resp = self.session.get(
                f"{GAMMA_API_BASE}/markets",
                params={
                    "limit": 50,
                    "active": "true",
                    "closed": "false",
                    "order": "volume",
                    "ascending": "false",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("markets", data.get("data", []))
            for item in items[:limit]:
                markets.append(Market(item))
        except Exception as e:
            logger.warning(f"Error fetching trending markets: {e}")
        return markets
