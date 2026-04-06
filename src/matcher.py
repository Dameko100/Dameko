"""
Keyword matcher: extracts search queries from news articles
to find relevant Polymarket prediction markets.
"""

import re
import logging
from typing import List, Tuple
from src.news_fetcher import Article

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Named entity / topic extraction patterns
# ---------------------------------------------------------------------------

# Countries and geopolitical actors that appear frequently in prediction markets
GEO_ENTITIES = [
    "Ukraine", "Russia", "China", "Taiwan", "Iran", "Israel", "Gaza", "Palestine",
    "Hamas", "Hezbollah", "NATO", "EU", "Europe", "USA", "United States", "North Korea",
    "South Korea", "Japan", "India", "Pakistan", "Saudi Arabia", "Turkey", "Syria",
    "Venezuela", "Brazil", "Mexico", "Africa",
]

# Political figures commonly on Polymarket
POLITICAL_FIGURES = [
    "Trump", "Biden", "Harris", "Zelensky", "Putin", "Xi Jinping", "Netanyahu",
    "Macron", "Scholz", "Modi", "Erdogan", "Milei", "Lula", "AMLO", "Musk",
]

# Finance / economy keywords
FINANCE_KEYWORDS = [
    "Fed", "Federal Reserve", "interest rate", "inflation", "recession", "GDP",
    "S&P 500", "Nasdaq", "bitcoin", "ethereum", "crypto", "oil", "gold",
    "dollar", "euro", "yen", "IPO", "earnings",
]

# Tech / AI keywords
TECH_KEYWORDS = [
    "ChatGPT", "GPT-5", "OpenAI", "Anthropic", "Google Gemini", "Meta AI",
    "Apple", "Microsoft", "Nvidia", "Tesla", "SpaceX", "Starlink",
    "artificial intelligence", "AI regulation", "cryptocurrency",
]

# Sports / entertainment that appear on Polymarket
SPORTS_KEYWORDS = [
    "Super Bowl", "World Cup", "Champions League", "NBA Finals", "World Series",
    "Wimbledon", "Tour de France", "Olympics", "UFC", "Formula 1",
]

# High-impact event keywords
EVENT_KEYWORDS = [
    "war", "ceasefire", "invasion", "attack", "bomb", "missile", "nuclear",
    "election", "vote", "referendum", "impeach", "resign", "coup",
    "pandemic", "outbreak", "vaccine", "earthquake", "hurricane",
    "sanctions", "tariff", "trade war", "default", "bankruptcy",
    "merger", "acquisition", "arrest", "indictment", "verdict",
]

ALL_ENTITY_LISTS = [
    GEO_ENTITIES,
    POLITICAL_FIGURES,
    FINANCE_KEYWORDS,
    TECH_KEYWORDS,
    SPORTS_KEYWORDS,
]


class ArticleMatcher:
    """
    Extracts keywords from an article and generates Polymarket search queries.
    Strategy:
      1. Extract named entities / known keywords from title + summary.
      2. Combine them into targeted queries.
      3. Fall back to category-based generic queries.
    """

    def get_queries(self, article: Article, max_queries: int = 4) -> List[str]:
        """Return a list of search queries to try on Polymarket."""
        text = f"{article.title} {article.summary}"
        queries: List[str] = []

        # 1. Find known named entities in the article text
        found_entities = self._extract_known_entities(text)

        # 2. Build targeted queries from entity combinations
        if found_entities:
            # Best: pair an event keyword with a geo/person entity
            event_kws = [e for e in found_entities if e.lower() in [k.lower() for k in EVENT_KEYWORDS]]
            entity_kws = [e for e in found_entities if e not in event_kws]

            if event_kws and entity_kws:
                queries.append(f"{entity_kws[0]} {event_kws[0]}")
            elif entity_kws:
                queries.append(entity_kws[0])
                if len(entity_kws) > 1:
                    queries.append(f"{entity_kws[0]} {entity_kws[1]}")
            elif event_kws:
                queries.append(event_kws[0])

        # 3. Add first few significant words from the title
        title_query = self._title_to_query(article.title)
        if title_query and title_query not in queries:
            queries.append(title_query)

        # 4. Category fallback
        category_query = self._category_fallback(article.category)
        if category_query and category_query not in queries:
            queries.append(category_query)

        return queries[:max_queries]

    def _extract_known_entities(self, text: str) -> List[str]:
        """Find known named entities present in the text."""
        found = []
        text_lower = text.lower()
        for entity_list in ALL_ENTITY_LISTS:
            for entity in entity_list:
                if entity.lower() in text_lower and entity not in found:
                    found.append(entity)
        return found

    def _title_to_query(self, title: str) -> str:
        """
        Take first 3-4 meaningful words from title as a query.
        Remove stop words and short tokens.
        """
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "are", "was",
            "were", "be", "been", "has", "have", "had", "will", "would",
            "could", "should", "may", "might", "can", "do", "does", "did",
            "its", "it", "this", "that", "these", "those", "he", "she", "they",
            "his", "her", "their", "our", "your", "my", "says", "said",
        }
        # Remove punctuation
        clean = re.sub(r"[^\w\s]", " ", title)
        words = [w for w in clean.split() if w.lower() not in stop_words and len(w) > 2]
        return " ".join(words[:4])

    def _category_fallback(self, category: str) -> str:
        """Return a generic high-relevance query for the article's category."""
        fallbacks = {
            "finance": "economy recession interest rate",
            "technology": "AI technology regulation",
            "politics": "election president",
            "world": "geopolitics conflict",
            "wars_conflicts": "war ceasefire",
            "ai": "artificial intelligence ChatGPT",
            "crypto": "bitcoin ethereum price",
            "general": "world news",
        }
        return fallbacks.get(category, "")


def score_article_importance(article: Article) -> float:
    """
    Heuristic score 0-1 indicating how likely an article
    will have related Polymarket markets.
    Higher score = send notification with higher priority.
    """
    score = 0.0
    text = f"{article.title} {article.summary}".lower()

    # High-value categories
    high_value_categories = {"politics", "finance", "wars_conflicts", "crypto", "ai"}
    if article.category in high_value_categories:
        score += 0.3

    # Known high-impact keywords
    impact_keywords = [
        "election", "war", "ceasefire", "attack", "president", "fed",
        "interest rate", "bitcoin", "crash", "sanctions", "resign",
        "win", "lose", "vote", "nuclear", "invasion", "deal", "treaty",
        "arrest", "indicted", "verdict", "ban", "regulation",
    ]
    for kw in impact_keywords:
        if kw in text:
            score += 0.1
            if score >= 0.8:
                break

    # Boost for named geopolitical entities
    for entity in GEO_ENTITIES + POLITICAL_FIGURES:
        if entity.lower() in text:
            score += 0.05
            if score >= 0.9:
                break

    return min(score, 1.0)
