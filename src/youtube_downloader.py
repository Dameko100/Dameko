"""
YouTube Music Downloader

Downloads audio from YouTube videos as MP3 files using yt-dlp.
Designed to be called from a Telegram bot handler.
"""

import os
import re
import logging
import tempfile
from dataclasses import dataclass
from typing import Optional

import yt_dlp

logger = logging.getLogger(__name__)

# Maximum file size Telegram allows for audio (50 MB)
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Regex to validate YouTube URLs
YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"[\w\-]{11}"
)


@dataclass
class TrackInfo:
    title: str
    artist: str
    duration_seconds: int
    thumbnail_url: Optional[str]
    file_path: str


def is_youtube_url(text: str) -> bool:
    """Return True if *text* looks like a YouTube URL."""
    return bool(YOUTUBE_URL_RE.search(text.strip()))


def download_audio(url: str, output_dir: str) -> TrackInfo:
    """
    Download the audio from a YouTube URL and convert it to MP3.

    Args:
        url: YouTube video URL.
        output_dir: Directory where the MP3 file will be saved.

    Returns:
        TrackInfo with metadata and the path to the downloaded MP3.

    Raises:
        ValueError: If the URL is invalid or video is unavailable.
        RuntimeError: If download or conversion fails.
    """
    if not is_youtube_url(url):
        raise ValueError("La URL no parece ser de YouTube.")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,  # only download the single video, not playlists
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        logger.error("yt-dlp download error: %s", exc)
        raise RuntimeError(f"No se pudo descargar el video: {exc}") from exc

    title = info.get("title", "Desconocido")
    artist = info.get("uploader") or info.get("channel") or "Desconocido"
    duration = int(info.get("duration") or 0)
    thumbnail = info.get("thumbnail")

    # yt-dlp renames the file after post-processing; find the MP3
    mp3_path = _find_mp3(output_dir, title)

    if mp3_path is None:
        raise RuntimeError("No se encontró el archivo MP3 después de la conversión.")

    file_size = os.path.getsize(mp3_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        os.remove(mp3_path)
        raise ValueError(
            f"El archivo pesa {file_size // (1024 * 1024)} MB, "
            f"lo que supera el límite de {MAX_FILE_SIZE_MB} MB de Telegram."
        )

    return TrackInfo(
        title=title,
        artist=artist,
        duration_seconds=duration,
        thumbnail_url=thumbnail,
        file_path=mp3_path,
    )


def _find_mp3(directory: str, title: str) -> Optional[str]:
    """Return the path of the first MP3 in *directory*, preferring one whose
    name contains *title*."""
    mp3_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".mp3")
    ]
    if not mp3_files:
        return None
    # Prefer a file whose name matches the title
    for path in mp3_files:
        if title[:20].lower() in os.path.basename(path).lower():
            return path
    return mp3_files[0]


def make_temp_dir() -> str:
    """Create and return a temporary directory for downloads."""
    return tempfile.mkdtemp(prefix="dameko_yt_")
