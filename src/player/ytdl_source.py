import asyncio

import discord
import yt_dlp as youtube_dl

from src.config import COOKIES_FILE, VERBOSE_MODE

# YouTube DL options

ytdl_format_options = {
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

FFMPEG_BEFORE_OPTIONS = "-nostdin"
FFMPEG_OPTIONS = "-vn -loglevel quiet"

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    """A source for playing audio from YouTube.

    This class extends discord.PCMVolumeTransformer to provide functionality
    for downloading and streaming audio from YouTube videos.
    """

    def __init__(self, source, *, data, volume=0.5):
        """Initialize a YTDLSource.

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
    async def from_url(cls, url, *, loop=None, stream=False, volume=0.5):
        """Create a YTDLSource from a URL.

        Args:
            url: The URL of the YouTube video or a search query.
            loop: The event loop to use for downloading.
            stream: Whether to stream the audio instead of downloading it.
            volume: The initial volume level (0.0 to 1.0).

        Returns:
            A YTDLSource instance.

        Raises:
            Exception: If there's an error extracting information from the URL.
        """
        loop = loop or asyncio.get_event_loop()

        try:
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=not stream)
            )
        except Exception as e:
            raise Exception(f"Could not extract info from {url}: {str(e)}")

        if "entries" in data:
            # Take first item from a playlist
            data = data["entries"][0]

        if not data:
            raise Exception(f"Could not retrieve any data from {url}")

        if "url" not in data and not stream:
            raise Exception(f"No URL found in extracted data from {url}")

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(
                filename, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS
            ),
            data=data,
            volume=volume,
        )

    @classmethod
    async def from_playlist(cls, url, *, loop=None, stream=False, volume=0.5):
        """Create multiple YTDLSource instances from a playlist URL.

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
            Exception: If there's an error extracting information from the URL or if no valid entries were found.
        """
        loop = loop or asyncio.get_event_loop()

        try:
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=not stream)
            )
        except Exception as e:
            raise Exception(f"Could not extract info from playlist {url}: {str(e)}")

        if "entries" not in data:
            # Not a playlist, just return a single source
            try:
                source = await cls.from_url(url, loop=loop, stream=stream, volume=volume)
                return [source], []
            except Exception as e:
                raise Exception(f"Could not extract info from {url}: {str(e)}")

        sources = []
        skipped_entries = []

        for entry in data["entries"]:
            if not entry:
                continue

            try:
                if "url" not in entry and not stream:
                    continue

                # Get video title or ID for error reporting
                video_title = entry.get("title", entry.get("id", "Unknown video"))

                filename = entry["url"] if stream else ytdl.prepare_filename(entry)
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
                error_msg = f"Could not extract any valid entries from playlist {url}. Skipped entries:\n"
                error_msg += "\n".join(skipped_entries)
                raise Exception(error_msg)
            else:
                raise Exception(f"Could not extract any valid entries from playlist {url}")

        return sources, skipped_entries
