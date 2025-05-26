import asyncio
import re
from typing import List, Optional, Tuple, Dict, Any, Union

import discord
import yt_dlp as youtube_dl

from src.config import COOKIES_FILE, VERBOSE_MODE

# Constants
MUSIC_YOUTUBE_PATTERN = r"music\.youtube\.com"
YOUTUBE_REPLACEMENT = "youtube.com"

# FFmpeg configuration
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
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
    "http_chunk_size": 10485760,  # 10MB chunking for better streaming
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


class SongInfo:
    """
    A class to store metadata about a song without creating the actual source.

    This class is used to store information in the queue until the song is ready to be played,
    at which point a YTDLSource will be created from this metadata.
    """

    def __init__(self, data: Dict[str, Any], volume: float = 0.5, stream: bool = True):
        """
        Initialize a SongInfo instance.

        Args:
            data: The data dictionary from youtube-dl.
            volume: The volume level to use when creating a source.
            stream: Whether to stream the audio instead of downloading it.
        """
        self.data = data
        self.title = data.get("title", "Unknown title")
        self.url = data.get("webpage_url", data.get("url", ""))
        self.volume = volume
        self.stream = stream

    async def create_source(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> "YTDLSource":
        """
        Create a YTDLSource from this SongInfo.

        Args:
            loop: The event loop to use for downloading.

        Returns:
            A YTDLSource instance.
        """
        # Get or create an event loop
        loop = loop or asyncio.get_event_loop()

        try:
            # If we're streaming, we need to get the direct audio URL
            if self.stream and "url" not in self.data:
                # Extract info using yt-dlp in a non-blocking way
                data = await loop.run_in_executor(
                    None, lambda: ytdl.extract_info(self.url, download=False)
                )
                if not data:
                    raise Exception(f"No data returned for {self.url}. The video might be unavailable.")
                self.data = data

            # Get the filename or URL for the audio
            filename = self.data["url"] if self.stream else ytdl.prepare_filename(self.data)

            # Create and return a new YTDLSource instance
            return YTDLSource(
                discord.FFmpegPCMAudio(
                    filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
                ),
                data=self.data,
                volume=self.volume,
            )
        except Exception as e:
            raise Exception(f"Could not create source from {self.url}: {str(e)}") from e


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
        create_source: bool = False,
    ) -> Union["YTDLSource", "SongInfo"]:
        """
        Create a SongInfo or YTDLSource from a URL.

        Args:
            url: The URL of the YouTube video.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).
            create_source: Whether to create a YTDLSource immediately (True) or return a SongInfo (False).

        Returns:
            A SongInfo instance if create_source is False, otherwise a YTDLSource instance.

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

        # Create a SongInfo instance
        song_info = SongInfo(data, volume=volume, stream=stream)

        # If create_source is True, create and return a YTDLSource immediately
        if create_source:
            return await song_info.create_source(loop=loop)

        # Otherwise, return the SongInfo
        return song_info

    @classmethod
    async def from_playlist(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = False,
        volume: float = 0.5,
        create_source: bool = False,
    ) -> Tuple[List[Union["YTDLSource", "SongInfo"]], List[str]]:
        """
        Create multiple SongInfo or YTDLSource instances from a playlist URL.

        Args:
            url: The URL of the YouTube playlist.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).
            create_source: Whether to create YTDLSource instances immediately (True) or return SongInfo instances (False).

        Returns:
            A tuple containing:
            - A list of SongInfo instances (or YTDLSource if create_source is True), one for each valid video in the playlist.
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
                source = await cls.from_url(url, loop=loop, stream=stream, volume=volume, create_source=create_source)
                return [source], []
            except Exception as e:
                raise Exception(f"Could not extract info from {url}: {str(e)}") from e

        sources = []
        skipped_entries: List[str] = []

        # Process each entry in the playlist
        for entry in data["entries"]:
            if not entry:
                continue

            try:
                # Get video title or ID for error reporting
                video_title = entry.get("title", entry.get("id", "Unknown video"))

                # Create a SongInfo instance
                song_info = SongInfo(entry, volume=volume, stream=stream)

                # If create_source is True, create a YTDLSource immediately
                if create_source:
                    source = await song_info.create_source(loop=loop)
                    sources.append(source)
                else:
                    sources.append(song_info)

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
