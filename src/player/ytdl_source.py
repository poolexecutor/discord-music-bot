import re
import asyncio
from typing import List, Optional, Tuple, Dict, Any, Union

import discord
import yt_dlp as youtube_dl
from loguru import logger

from src.config import COOKIES_FILE, VERBOSE_MODE

# Constants
MUSIC_YOUTUBE_PATTERN = r"music\.youtube\.com"
YOUTUBE_REPLACEMENT = "youtube.com"
STREAMING_TIMEOUT = 60  # Timeout for streaming operations in seconds
URL_EXPIRATION_TIME = 3600  # Cached URL expiration time in seconds

# FFmpeg configuration
FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -timeout 10000000"
)
FFMPEG_OPTIONS = "-vn -loglevel warning -bufsize 64k"

# Default YouTube-DL options
DEFAULT_YTDL_OPTIONS: Dict[str, Any] = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # IPv4 support
    "cookiefile": COOKIES_FILE if COOKIES_FILE else None,
    "http_chunk_size": 10485760,  # 10MB chunks for better streaming
    "geo_bypass": True,
    "retries": 10,
    "socket_timeout": STREAMING_TIMEOUT,
    "extract_flat": True,  # Faster metadata extraction for playlists
    "skip_download": True,  # Avoids actual file downloading
    "logtostderr": VERBOSE_MODE,
    "quiet": not VERBOSE_MODE,
    "no_warnings": not VERBOSE_MODE,
    "verbose": VERBOSE_MODE,
}

# Global YouTube-DL instance
ytdl = youtube_dl.YoutubeDL(DEFAULT_YTDL_OPTIONS)


def convert_music_youtube_url(url: str) -> str:
    """
    Convert URLs from music.youtube.com to youtube.com.
    """
    if re.search(MUSIC_YOUTUBE_PATTERN, url):
        logger.debug(f"Converting music.youtube.com URL to youtube.com: {url}")
        return re.sub(MUSIC_YOUTUBE_PATTERN, YOUTUBE_REPLACEMENT, url)
    return url


class SongInfo:
    """
    Class for managing metadata related to a YouTube song/video.
    """

    def __init__(
        self,
        url: str,
        volume: float = 0.5,
        stream: bool = True,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.volume = volume
        self.stream = stream
        self.data = data
        self.title = data.get("title", "Unknown Title") if data else "Loading..."

        logger.debug(f"Created SongInfo: URL: {url}, Title: {self.title}")

    async def extract_info(
        self, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> Dict[str, Any]:
        """
        Extract song metadata using yt-dlp.
        """
        loop = loop or asyncio.get_event_loop()
        extraction_options = DEFAULT_YTDL_OPTIONS.copy()
        extraction_options.update(
            {
                "extract_flat": not self.stream,
                "noplaylist": True,
                "skip_download": self.stream,
            }
        )
        temp_ytdl = youtube_dl.YoutubeDL(extraction_options)

        try:
            logger.debug(f"Extracting info for URL: {self.url}")
            self.data = await loop.run_in_executor(
                None, lambda: temp_ytdl.extract_info(self.url, download=not self.stream)
            )

            if not self.data:
                raise ValueError(
                    f"No data returned for {self.url}. The video might be unavailable."
                )

            self.title = self.data.get("title", "Unknown Title")
            logger.info(f"Successfully extracted info: {self.title}")
            return self.data

        except Exception as exc:
            logger.error(f"Failed to extract info for {self.url}: {exc}")
            raise

    async def create_source(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> "YTDLSource":
        """
        Create a YTDLSource instance for audio playback.
        """
        loop = loop or asyncio.get_event_loop()

        # Re-extract information if needed (e.g., streaming URL expired)
        if not self.data or (self.stream and "url" not in self.data):
            self.data = await self.extract_info(loop=loop)

        # Ensure a valid streaming URL or local filename is available
        filename = self.data.get("url") if self.stream else ytdl.prepare_filename(self.data)
        if not filename:
            raise ValueError(f"No audio source found for {self.title}")

        logger.debug(f"Creating audio source with filename: {filename}")

        # Create FFmpeg audio stream
        source = YTDLSource(
            discord.FFmpegPCMAudio(
                filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
            ),
            data=self.data,
            volume=self.volume,
        )
        logger.info(f"Audio source created for: {self.title}")
        return source


class YTDLSource(discord.PCMVolumeTransformer):
    """
    A source for playing audio from a YouTube video.
    """

    def __init__(self, source: discord.AudioSource, *, data: Dict[str, Any], volume: float = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title", "Unknown Title")
        self.url = data.get("url", "")
        self.duration = data.get("duration", 0)

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = True,
        volume: float = 0.5,
    ) -> Union["YTDLSource", SongInfo]:
        """
        Create a SongInfo instance or YTDLSource from a given YouTube URL.
        """
        url = convert_music_youtube_url(url)
        logger.debug(f"Processing URL: {url}")

        loop = loop or asyncio.get_event_loop()
        basic_options = DEFAULT_YTDL_OPTIONS.copy()
        basic_options.update({"extract_flat": True, "skip_download": True, "noplaylist": True})
        temp_ytdl = youtube_dl.YoutubeDL(basic_options)

        try:
            # Extract basic info
            data = await loop.run_in_executor(
                None, lambda: temp_ytdl.extract_info(url, download=False)
            )
            if not data:
                raise ValueError(f"Failed to get data for URL: {url}")

            # If 'url' is already extracted, return YTDLSource immediately
            song_info = SongInfo(url=url, volume=volume, stream=stream, data=data)
            if stream:
                return await song_info.create_source(loop=loop)

            return song_info

        except Exception as exc:
            logger.error(f"Error processing {url}: {exc}")
            raise

    @classmethod
    async def from_playlist(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = True,
        volume: float = 0.5,
    ) -> Tuple[List[Union["YTDLSource", SongInfo]], List[str]]:
        """
        Create multiple SongInfo or YTDLSource instances from a YouTube playlist URL.
        """
        url = convert_music_youtube_url(url)
        logger.info(f"Processing playlist: {url}")

        loop = loop or asyncio.get_event_loop()
        playlist_options = DEFAULT_YTDL_OPTIONS.copy()
        playlist_options.update({"extract_flat": True, "noplaylist": False})
        temp_ytdl = youtube_dl.YoutubeDL(playlist_options)

        try:
            # Extract playlist data
            data = await loop.run_in_executor(
                None, lambda: temp_ytdl.extract_info(url, download=False)
            )
            if not data or "entries" not in data:
                logger.warning(f"No valid playlist entries found for {url}")
                return [], [f"No valid entries for playlist: {url}"]

            sources: List[Union["YTDLSource", SongInfo]] = []
            skipped = []

            for entry in data["entries"]:
                try:
                    if not entry:
                        continue
                    source = await cls.from_url(
                        entry["url"], loop=loop, stream=stream, volume=volume
                    )
                    sources.append(source)
                except Exception as exc:
                    skipped.append(str(exc))

            return sources, skipped

        except Exception as exc:
            logger.error(f"Error processing playlist {url}: {exc}")
            raise
