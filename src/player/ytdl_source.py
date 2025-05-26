import asyncio
import re
from typing import List, Optional, Tuple, Dict, Any

import discord
import yt_dlp as youtube_dl

from src.config import COOKIES_FILE, VERBOSE_MODE

# Constants
MUSIC_YOUTUBE_PATTERN = r"music\.youtube\.com"
YOUTUBE_REPLACEMENT = "youtube.com"

# FFmpeg configuration
FFMPEG_BEFORE_OPTIONS = "-nostdin"
FFMPEG_OPTIONS = "-vn -loglevel quiet"

# YouTube DL options
ytdl_format_options: Dict[str, Any] = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,  # Allow playlists
    "nocheckcertificate": True,
    "ignoreerrors": True,  # Skip videos that cause errors in playlists
    "logtostderr": VERBOSE_MODE,  # Log to stderr if verbose mode is enabled
    "quiet": not VERBOSE_MODE,  # Be quiet if verbose mode is disabled
    "no_warnings": not VERBOSE_MODE,  # Show warnings if verbose mode is enabled
    "verbose": VERBOSE_MODE,  # Full verbosity if verbose mode is enabled
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "cookiefile": COOKIES_FILE if COOKIES_FILE else None,
}

# Initialize YouTube DL with our options
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def convert_music_youtube_url(url: str) -> str:
    """
    Convert music.youtube.com URLs to regular youtube.com URLs.

    Args:
        url: The YouTube URL to process

    Returns:
        The converted URL with youtube.com domain instead of music.youtube.com
    """
    if re.search(MUSIC_YOUTUBE_PATTERN, url):
        return re.sub(MUSIC_YOUTUBE_PATTERN, YOUTUBE_REPLACEMENT, url)
    return url


class YTDLSource(discord.PCMVolumeTransformer):
    """
    A source for playing audio from YouTube.

    This class extends discord.PCMVolumeTransformer to provide functionality
    for downloading and streaming audio from YouTube videos.
    """

    def __init__(self, source: discord.AudioSource, *, data: Dict[str, Any], volume: float = 0.5):
        """
        Initialize a YTDLSource.

        Args:
            source: The audio source.
            data: The data dictionary from youtube-dl.
            volume: The initial volume level (0.0 to 1.0).
        """
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title", "Unknown title")
        self.url = data.get("url", "")

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = False,
        volume: float = 0.5,
    ) -> "YTDLSource":
        """
        Create a YTDLSource from a URL.

        Args:
            url: The URL of the YouTube video.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).

        Returns:
            A YTDLSource instance.

        Raises:
            Exception: If there's an error extracting information from the URL or
                       if the video is unavailable.
        """
        # Convert music.youtube.com URLs to youtube.com
        url = convert_music_youtube_url(url)

        # Get or create an event loop
        loop = loop or asyncio.get_event_loop()

        try:
            # Extract info using yt-dlp in a non-blocking way
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=not stream)
            )
        except Exception as e:
            raise Exception(f"Could not extract info from {url}: {str(e)}") from e

        if not data:
            raise Exception(f"No data returned for {url}. The video might be unavailable.")

        if "entries" in data:
            # Take first item from a playlist
            data = data["entries"][0]
            if not data:
                raise Exception(f"No valid entries found in playlist at {url}")

        if "url" not in data:
            raise Exception(f"No playable URL found for {url}. The video might be unavailable.")

        # Get the filename or URL for the audio
        filename = data["url"] if stream else ytdl.prepare_filename(data)

        # Create and return a new YTDLSource instance
        return cls(
            discord.FFmpegPCMAudio(
                filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
            ),
            data=data,
            volume=volume,
        )

    @classmethod
    async def from_playlist(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = False,
        volume: float = 0.5,
    ) -> Tuple[List["YTDLSource"], List[str]]:
        """
        Create multiple YTDLSource instances from a playlist URL.

        Args:
            url: The URL of the YouTube playlist.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).

        Returns:
            A tuple containing:
            - A list of YTDLSource instances, one for each valid video in the playlist.
            - A list of error messages for videos that couldn't be processed.

        Raises:
            Exception: If there's an error extracting information from the URL or
                       if no valid entries were found.
        """
        # Convert music.youtube.com URLs to youtube.com
        url = convert_music_youtube_url(url)

        # Get or create an event loop
        loop = loop or asyncio.get_event_loop()

        try:
            # Extract info from the playlist
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=not stream)
            )
        except Exception as e:
            raise Exception(f"Could not extract info from playlist {url}: {str(e)}") from e

        if "entries" not in data:
            # Not a playlist, just return a single source
            try:
                source = await cls.from_url(url, loop=loop, stream=stream, volume=volume)
                return [source], []
            except Exception as e:
                raise Exception(f"Could not extract info from {url}: {str(e)}") from e

        sources: List[YTDLSource] = []
        skipped_entries: List[str] = []

        # Process each entry in the playlist
        for entry in data["entries"]:
            if not entry:
                continue

            try:
                if "url" not in entry and not stream:
                    continue

                # Get video title or ID for error reporting
                video_title = entry.get("title", entry.get("id", "Unknown video"))

                # Get the filename or URL for the audio
                filename = entry["url"] if stream else ytdl.prepare_filename(entry)

                # Create a new YTDLSource instance
                source = cls(
                    discord.FFmpegPCMAudio(
                        filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
                    ),
                    data=entry,
                    volume=volume,
                )
                sources.append(source)
            except Exception as e:
                # Skip this entry but record the error
                error_message = f"Skipped '{video_title}': {str(e)}"
                skipped_entries.append(error_message)
                continue

        if not sources:
            if skipped_entries:
                # All entries were skipped due to errors
                error_msg = (
                    f"Could not extract any valid entries from playlist {url}. Skipped entries:\n"
                )
                error_msg += "\n".join(skipped_entries)
                raise Exception(error_msg)
            else:
                raise Exception(f"Could not extract any valid entries from playlist {url}")

        return sources, skipped_entries
