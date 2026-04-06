"""
Telegram notifier: formats and sends news + Polymarket alerts via Bot API.
Uses the synchronous requests-based approach for simplicity in a scheduled loop.
"""

import requests
import logging
from typing import List, Optional
from src.news_fetcher import Article
from src.polymarket import Market

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Category -> emoji mapping
CATEGORY_EMOJI = {
    "finance": "💰",
    "technology": "💻",
    "politics": "🏛️",
    "world": "🌍",
    "wars_conflicts": "⚔️",
    "ai": "🤖",
    "crypto": "₿",
    "general": "📰",
}


class TelegramNotifier:
    """Sends formatted Telegram messages to a chat."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = requests.Session()

    def _api_url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.bot_token, method=method)

    def send_message(self, text: str, disable_preview: bool = False) -> bool:
        """Send a raw Markdown message. Returns True on success."""
        try:
            resp = self.session.post(
                self._api_url("sendMessage"),
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": disable_preview,
                },
                timeout=10,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"Telegram send failed: {data.get('description')}")
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram request error: {e}")
            return False

    def send_news_alert(self, article: Article, markets: List[Market]) -> bool:
        """
        Send a formatted alert for a news article with related Polymarket links.
        """
        emoji = CATEGORY_EMOJI.get(article.category, "📰")
        category_label = article.category.replace("_", " ").title()

        lines = [
            f"{emoji} *{_md(category_label)}*",
            "",
            f"*{_md(article.title)}*",
            "",
        ]

        if article.summary:
            lines.append(f"_{_md(article.summary[:250])}_")
            lines.append("")

        lines.append(f"🔗 [Leer noticia]({article.url})")
        lines.append(f"📡 Fuente: {_md(article.source)}")

        if markets:
            lines.append("")
            lines.append("─────────────────────────")
            lines.append("📊 *Mercados relacionados en Polymarket:*")
            lines.append("")
            for m in markets[:4]:
                market_line = f"• [{_md(m.question[:80])}]({m.url})"
                if m.odds_summary:
                    market_line += f"\n  └ _{_md(m.odds_summary)}_"
                if m.volume > 0:
                    vol_str = f"${m.volume:,.0f}"
                    market_line += f" \\| Vol: {_md(vol_str)}"
                lines.append(market_line)
        else:
            lines.append("")
            lines.append("_No se encontraron mercados relacionados en Polymarket\\._")

        text = "\n".join(lines)
        return self.send_message(text)

    def send_digest(self, markets: List[Market], title: str = "Mercados Trending") -> bool:
        """Send a digest of trending Polymarket markets."""
        lines = [
            f"🔥 *{_md(title)}*",
            f"_Top mercados activos en Polymarket_",
            "",
        ]
        for i, m in enumerate(markets[:8], 1):
            line = f"{i}\\. [{_md(m.question[:70])}]({m.url})"
            if m.odds_summary:
                line += f"\n   _{_md(m.odds_summary)}_"
            if m.volume > 0:
                line += f" \\| 💧 {_md(f'${m.volume:,.0f}')}"
            lines.append(line)
            lines.append("")

        return self.send_message("\n".join(lines))

    def send_startup_message(self) -> bool:
        """Announce bot is running."""
        text = (
            "🚀 *Dameko News Bot iniciado*\n\n"
            "Monitoreando noticias de:\n"
            "💰 Finanzas · 💻 Tecnología · 🏛️ Política\n"
            "⚔️ Conflictos · 🤖 IA · ₿ Crypto · 🌍 Mundo\n\n"
            "Recibirás alertas con mercados de Polymarket relacionados\\."
        )
        return self.send_message(text)

    def test_connection(self) -> bool:
        """Verify the bot token and chat ID are working."""
        try:
            resp = self.session.get(self._api_url("getMe"), timeout=10)
            data = resp.json()
            if data.get("ok"):
                bot_name = data["result"].get("username", "unknown")
                logger.info(f"Telegram bot connected: @{bot_name}")
                return True
            logger.error(f"Telegram getMe failed: {data.get('description')}")
            return False
        except Exception as e:
            logger.error(f"Telegram connection test error: {e}")
            return False


def _md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    result = ""
    for char in str(text):
        if char in special:
            result += f"\\{char}"
        else:
            result += char
    return result
