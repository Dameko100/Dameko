"""
Dameko YouTube Music Bot
========================
A Telegram bot that downloads YouTube videos as MP3 and sends them to the user.

Usage:
    python youtube_music_bot.py

Required environment variables (add to .env):
    TELEGRAM_BOT_TOKEN   - Telegram bot token from @BotFather
    TELEGRAM_CHAT_ID     - (optional) restrict to a specific chat

How to use the bot on your phone:
    1. Open Telegram and search for your bot.
    2. Send /start to begin.
    3. Paste any YouTube URL and receive the MP3 audio file.
"""

import logging
import os
import shutil

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.youtube_downloader import (
    TrackInfo,
    download_audio,
    is_youtube_url,
    make_temp_dir,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("yt_music_bot")

BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    await update.message.reply_text(
        "Hola! Soy el bot de musica de Dameko.\n\n"
        "Enviame el enlace de cualquier video de YouTube y te mando el audio en MP3.\n\n"
        "Ejemplo:\n"
        "  https://youtu.be/dQw4w9WgXcQ\n\n"
        "Comandos:\n"
        "  /start - Mostrar este mensaje\n"
        "  /ayuda - Instrucciones de uso"
    )


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help instructions."""
    await update.message.reply_text(
        "Como descargar musica:\n\n"
        "1. Ve a YouTube en tu celular.\n"
        "2. Abre el video que quieres.\n"
        "3. Toca Compartir > Copiar enlace.\n"
        "4. Pega el enlace aqui y envialo.\n"
        "5. Espera unos segundos y recibiras el MP3.\n\n"
        "Nota: Los archivos de mas de 50 MB no pueden enviarse por Telegram."
    )


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages. Downloads audio if a YouTube URL is detected."""
    text = (update.message.text or "").strip()

    if not is_youtube_url(text):
        await update.message.reply_text(
            "Eso no parece un enlace de YouTube. "
            "Enviame una URL como https://youtu.be/... o https://www.youtube.com/watch?v=..."
        )
        return

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text("Descargando... un momento.")

    tmp_dir = make_temp_dir()
    try:
        # Download
        await update.message.chat.send_action(ChatAction.UPLOAD_VOICE)
        track: TrackInfo = download_audio(text, tmp_dir)

        # Send the MP3
        caption = f"{track.title}\nArtista: {track.artist}"
        if track.duration_seconds:
            minutes, seconds = divmod(track.duration_seconds, 60)
            caption += f"\nDuracion: {minutes}:{seconds:02d}"

        with open(track.file_path, "rb") as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=track.title,
                performer=track.artist,
                duration=track.duration_seconds or None,
                caption=caption,
            )

        logger.info("Sent '%s' to chat %s", track.title, update.message.chat_id)

    except ValueError as exc:
        await update.message.reply_text(f"No se pudo descargar: {exc}")
        logger.warning("ValueError for %s: %s", text, exc)
    except RuntimeError as exc:
        await update.message.reply_text(
            f"Ocurrio un error al descargar el audio: {exc}"
        )
        logger.error("RuntimeError for %s: %s", text, exc)
    except Exception as exc:
        await update.message.reply_text(
            "Ocurrio un error inesperado. Por favor intenta de nuevo."
        )
        logger.exception("Unexpected error for %s: %s", text, exc)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting Dameko YouTube Music Bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot running. Send a YouTube URL to download music. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
