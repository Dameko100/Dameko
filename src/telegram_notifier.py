"""
Telegram notifier: formats and sends news + Polymarket alerts via Bot API.
Uses HTML parse mode (more reliable than MarkdownV2 for arbitrary content).
"""

import requests
import logging
from typing import List, Optional
from src.news_fetcher import Article
from src.polymarket import Market

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

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


def _h(text: str) -> str:
    """Escape text for Telegram HTML mode."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class TelegramNotifier:
    """Sends formatted Telegram messages to a chat."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = requests.Session()

    def _api_url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.bot_token, method=method)

    def send_message(self, text: str, disable_preview: bool = True) -> bool:
        """Send an HTML-formatted message. Returns True on success."""
        try:
            resp = self.session.post(
                self._api_url("sendMessage"),
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
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
        """Send a formatted alert for a news article with related Polymarket links."""
        emoji = CATEGORY_EMOJI.get(article.category, "📰")
        category_label = article.category.replace("_", " ").title()

        lines = [
            f"{emoji} <b>{_h(category_label)}</b>",
            "",
            f"<b>{_h(article.title)}</b>",
            "",
        ]

        if article.summary:
            lines.append(f"<i>{_h(article.summary[:300])}</i>")
            lines.append("")

        lines.append(f'🔗 <a href="{article.url}">Leer noticia</a>')
        lines.append(f"📡 Fuente: {_h(article.source)}")

        if markets:
            lines.append("")
            lines.append("─────────────────────")
            lines.append("📊 <b>Mercados en Polymarket:</b>")
            lines.append("")
            for m in markets[:4]:
                market_line = f'• <a href="{m.url}">{_h(m.question[:90])}</a>'
                if m.odds_summary:
                    market_line += f"\n  └ <i>{_h(m.odds_summary)}</i>"
                if m.volume > 0:
                    market_line += f" | Vol: <b>${m.volume:,.0f}</b>"
                lines.append(market_line)
        else:
            lines.append("")
            lines.append("<i>Sin mercados relacionados en Polymarket.</i>")

        return self.send_message("\n".join(lines))

    def send_digest(self, markets: List[Market], title: str = "Mercados Trending") -> bool:
        """Send a digest of trending Polymarket markets."""
        lines = [
            f"🔥 <b>{_h(title)}</b>",
            "<i>Top mercados activos en Polymarket</i>",
            "",
        ]
        for i, m in enumerate(markets[:8], 1):
            line = f'{i}. <a href="{m.url}">{_h(m.question[:80])}</a>'
            if m.odds_summary:
                line += f"\n   <i>{_h(m.odds_summary)}</i>"
            if m.volume > 0:
                line += f" | 💧 <b>${m.volume:,.0f}</b>"
            lines.append(line)
            lines.append("")

        return self.send_message("\n".join(lines))

    def send_startup_message(self) -> bool:
        """Announce bot is running."""
        text = (
            "🚀 <b>Dameko News Bot iniciado</b>\n\n"
            "Monitoreando noticias de:\n"
            "💰 Finanzas · 💻 Tecnología · 🏛️ Política\n"
            "⚔️ Conflictos · 🤖 IA · ₿ Crypto · 🌍 Mundo\n\n"
            "Recibirás alertas con mercados de Polymarket relacionados."
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
