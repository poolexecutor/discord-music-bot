import asyncio
import re
from typing import List, Optional, Tuple, Dict, Any, Union

import discord
import yt_dlp as youtube_dl
from loguru import logger

from src.config import COOKIES_FILE, VERBOSE_MODE

# Constants
MUSIC_YOUTUBE_PATTERN = r"music\.youtube\.com"
YOUTUBE_REPLACEMENT = "youtube.com"

# FFmpeg configuration - improved for more reliable playback
FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -timeout 10000000"
)
FFMPEG_OPTIONS = "-vn -loglevel warning -bufsize 64k"

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
    "extract_flat": True,  # Only extract basic metadata for playlists (faster)
    "skip_download": True,  # Default to streaming mode
    "geo_bypass": True,  # Try to bypass geo-restrictions
    "retries": 10,  # Retry on HTTP errors
    "socket_timeout": 60,  # Increase timeout for slow connections
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
        logger.debug(f"Converting music.youtube.com URL to youtube.com: {url}")
        return re.sub(MUSIC_YOUTUBE_PATTERN, YOUTUBE_REPLACEMENT, url)
    return url


class SongInfo:
    """
    A class to store metadata about a song without creating the actual source.

    This class is used to store information in the queue until the song is ready to be played,
    at which point a YTDLSource will be created from this metadata.
    """

    def __init__(
        self,
        url: str,
        volume: float = 0.5,
        stream: bool = True,
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a SongInfo instance.

        Args:
            url: The URL of the video or stream.
            volume: The volume level to use when creating a source.
            stream: Whether to stream the audio instead of downloading it.
            data: Optional pre-extracted data dictionary from youtube-dl.
        """
        self.url = url
        self.volume = volume
        self.stream = stream
        self.data = data
        self.title = data.get("title", "Unknown title") if data else "Loading..."

        logger.debug(f"Created SongInfo for URL: {url}, Title: {self.title}")

    async def extract_info(
        self, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> Dict[str, Any]:
        """
        Extract information for the song using yt-dlp.

        Args:
            loop: The event loop to use for downloading.

        Returns:
            A dictionary containing extracted information.

        Raises:
            Exception: If information extraction fails.
        """
        logger.debug(f"Extracting info for URL: {self.url}")
        loop = loop or asyncio.get_event_loop()

        # Use different options for extraction vs. downloading
        extraction_options = ytdl_format_options.copy()
        extraction_options["extract_flat"] = not self.stream  # Full extraction only when streaming
        extraction_options["noplaylist"] = True  # We're handling a single song here
        extraction_options["skip_download"] = self.stream  # Skip download if streaming

        temp_ytdl = youtube_dl.YoutubeDL(extraction_options)

        try:
            data = await loop.run_in_executor(
                None, lambda: temp_ytdl.extract_info(self.url, download=not self.stream)
            )

            if not data:
                raise Exception(f"No data returned for {self.url}. The video might be unavailable.")

            self.data = data
            self.title = data.get("title", "Unknown title")
            logger.info(f"Successfully extracted info for: {self.title}")

            # Check if we have the required data for streaming
            if self.stream and "url" not in data:
                logger.warning(
                    f"No direct URL found in data for {self.title}, retrying with full extraction"
                )
                # Retry with full extraction
                extraction_options["extract_flat"] = False
                temp_ytdl = youtube_dl.YoutubeDL(extraction_options)

                data = await loop.run_in_executor(
                    None, lambda: temp_ytdl.extract_info(self.url, download=False)
                )

                if not data or "url" not in data:
                    raise Exception(f"Could not find direct URL for {self.url} after retry")

                self.data = data

            return data

        except Exception as e:
            logger.error(f"Failed to extract info for {self.url}: {str(e)}")
            raise Exception(f"Could not extract info from {self.url}: {str(e)}") from e

    async def create_source(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> "YTDLSource":
        """
        Create a YTDLSource from this SongInfo.

        Args:
            loop: The event loop to use for downloading.

        Returns:
            A YTDLSource instance.

        Raises:
            Exception: If source creation fails.
        """
        loop = loop or asyncio.get_event_loop()

        try:
            # Extract info if not already available
            if not self.data or (self.stream and "url" not in self.data):
                logger.debug(f"Need to extract info for {self.url} before creating source")
                await self.extract_info(loop=loop)

            # Get the filename or URL for the audio
            if self.stream:
                filename = self.data.get("url")
                if not filename:
                    logger.error(f"No URL found in data for {self.title}")
                    raise Exception(f"No direct URL found for {self.title}")
            else:
                filename = ytdl.prepare_filename(self.data)

            logger.debug(f"Creating audio source with filename: {filename}")

            # Create a PCM audio source with improved FFmpeg options
            ffmpeg_audio = discord.FFmpegPCMAudio(
                filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
            )

            # Create and return a new YTDLSource instance
            source = YTDLSource(
                ffmpeg_audio,
                data=self.data,
                volume=self.volume,
            )
            logger.info(f"Successfully created source for: {self.title}")
            return source

        except Exception as e:
            logger.error(f"Failed to create source for {self.url}: {str(e)}")
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
        self.duration = data.get("duration", 0)
        logger.debug(f"Initialized YTDLSource for: {self.title}, Duration: {self.duration}s")

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = True,  # Changed default to True for streaming
        volume: float = 0.5,
        create_source: bool = False,
    ) -> Union["YTDLSource", SongInfo]:
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
        logger.info(f"Processing URL: {url}, Stream: {stream}, Create Source: {create_source}")

        # Create a SongInfo instance with minimal data (lazy loading)
        song_info = SongInfo(url=url, volume=volume, stream=stream)

        # If immediate source creation is requested, extract info and create source
        if create_source:
            logger.debug(f"Creating source immediately for: {url}")
            return await song_info.create_source(loop=loop)

        # Otherwise, return the SongInfo for later processing
        return song_info

    @classmethod
    async def from_playlist(
        cls,
        url: str,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        stream: bool = True,  # Changed default to True for streaming
        volume: float = 0.5,
        create_source: bool = False,
    ) -> Tuple[List[Union["YTDLSource", SongInfo]], List[str]]:
        """
        Create multiple SongInfo or YTDLSource instances from a playlist URL.

        Args:
            url: The URL of the YouTube playlist.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).
            create_source: Whether to create YTDLSource instances immediately (True)
                           or return SongInfo instances (False).

        Returns:
            A tuple containing:
            - A list of SongInfo instances (or YTDLSource if create_source is True),
              one for each valid video in the playlist.
            - A list of error messages for videos that couldn't be processed.

        Raises:
            Exception: If there's an error extracting information from the URL or
                       if no valid entries were found.
        """
        # Convert music.youtube.com URLs to youtube.com
        url = convert_music_youtube_url(url)
        logger.info(f"Processing playlist URL: {url}")

        # Get or create an event loop
        loop = loop or asyncio.get_event_loop()

        try:
            # Set specific options for playlist extraction
            playlist_options = ytdl_format_options.copy()
            playlist_options["extract_flat"] = (
                "in_playlist"  # Don't extract full info for each video
            )
            playlist_options["noplaylist"] = False  # We want playlists

            temp_ytdl = youtube_dl.YoutubeDL(playlist_options)

            # Extract basic playlist info
            logger.debug(f"Extracting playlist info for: {url}")
            data = await loop.run_in_executor(
                None, lambda: temp_ytdl.extract_info(url, download=False)
            )

        except Exception as e:
            logger.error(f"Failed to extract playlist info from {url}: {str(e)}")
            raise Exception(f"Could not extract info from playlist {url}: {str(e)}") from e

        if "entries" not in data:
            # Not a playlist, just return a single source
            logger.info(f"URL {url} is not a playlist, processing as single video")
            try:
                source = await cls.from_url(
                    url, loop=loop, stream=stream, volume=volume, create_source=create_source
                )
                return [source], []
            except Exception as e:
                logger.error(f"Failed to process {url} as single video: {str(e)}")
                raise Exception(f"Could not extract info from {url}: {str(e)}") from e

        sources = []
        skipped_entries: List[str] = []

        entries = [entry for entry in data.get("entries", []) if entry]
        logger.info(f"Found {len(entries)} valid entries in playlist")

        # Process each entry in the playlist
        for entry in entries:
            try:
                # Get video title or ID for error reporting
                video_title = entry.get("title", entry.get("id", "Unknown video"))
                video_url = entry.get("url", entry.get("webpage_url", ""))

                if not video_url:
                    logger.warning(f"No URL found for entry {video_title}, skipping")
                    skipped_entries.append(f"Skipped '{video_title}': No URL found")
                    continue

                logger.debug(f"Processing playlist entry: {video_title}")

                # Create a SongInfo instance with minimal metadata
                song_info = SongInfo(
                    url=video_url,
                    volume=volume,
                    stream=stream,
                    data=entry,  # Use partial data from playlist extraction
                )

                # If create_source is True, create a YTDLSource immediately
                if create_source:
                    logger.debug(f"Creating source for playlist entry: {video_title}")
                    source = await song_info.create_source(loop=loop)
                    sources.append(source)
                else:
                    sources.append(song_info)

            except Exception as e:
                # Skip this entry but record the error
                video_title = entry.get("title", entry.get("id", "Unknown video"))
                error_message = f"Skipped '{video_title}': {str(e)}"
                logger.error(error_message)
                skipped_entries.append(error_message)
                continue

        if not sources:
            if skipped_entries:
                # All entries were skipped due to errors
                error_msg = (
                    f"Could not extract any valid entries from playlist {url}. Skipped entries:\n"
                )
                error_msg += "\n".join(skipped_entries)
                logger.error(error_msg)
                raise Exception(error_msg)
            else:
                error_msg = f"Could not extract any valid entries from playlist {url}"
                logger.error(error_msg)
                raise Exception(error_msg)

        logger.info(
            f"Successfully processed {len(sources)} out of {len(entries)} entries in playlist"
        )
        return sources, skipped_entries
