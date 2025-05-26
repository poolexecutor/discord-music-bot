import asyncio
from collections import deque

from discord.ext import commands
from loguru import logger

from src.config import DEFAULT_VOLUME
from src.player.queue_manager import play_next, queues, volumes
from src.player.ytdl_source import YTDLSource
from src.utils.youtube_api import search_youtube


class PlaybackCommands(commands.Cog):
    """Commands for controlling music playback.

    This cog provides commands for playing, pausing, resuming, stopping, and skipping songs.
    """

    def __init__(self, bot):
        """Initialize the PlaybackCommands cog.

        Args:
            bot: The Discord bot instance.
        """
        self.bot = bot
        logger.debug("PlaybackCommands cog initialized")

    @commands.command(name="play", help="To play a song or playlist (URL or search term)")
    async def play(self, ctx, *, query):
        """Play a song or playlist from a YouTube URL or search term.

        This command will:
        1. Search for the song if a search term is provided
        2. Add the song(s) to the server's queue
        3. Start playing if nothing is currently playing
        4. If a playlist URL is provided, add all songs from the playlist to the queue

        Args:
            ctx: The command context.
            query: The YouTube URL (video or playlist) or search term.

        Returns:
            None
        """
        try:
            server = ctx.message.guild
            server_id = server.id
            voice_channel = server.voice_client
            logger.info(
                f"Play command invoked by {ctx.author} in server {server.name} (ID: {server_id})"
            )
            logger.debug(f"Query: {query}")

            if not voice_channel:
                logger.warning(f"Bot not connected to voice channel in server {server.name}")
                await ctx.send("Bot is not connected to a voice channel. Use !join first.")
                return

            # Initialize queue for this server if it doesn't exist
            if server_id not in queues:
                logger.debug(f"Initializing queue for server {server.name}")
                queues[server_id] = deque()

            # Initialize volume for this server if it doesn't exist
            if server_id not in volumes:
                logger.debug(f"Initializing volume for server {server.name}")
                volumes[server_id] = DEFAULT_VOLUME  # Default to 50%

            async with ctx.typing():
                # Check if the query is a URL or a search term
                if not query.startswith("https://"):
                    logger.debug(f"Search query detected: {query}")
                    await ctx.send(f"Searching for: {query}...")

                    # Try to use authenticated YouTube API first
                    logger.debug("Attempting to search using authenticated YouTube API")
                    videos = await search_youtube(query)

                    if videos and len(videos) > 0:
                        # Use the first result from authenticated search
                        logger.info(f"Found video via API: {videos[0]['title']}")
                        await ctx.send(f"Found: {videos[0]['title']} (using your YouTube account)")
                        query = videos[0]["url"]
                        logger.debug(f"Using URL: {query}")
                    else:
                        # Fall back to yt-dlp search if API search fails
                        logger.warning("YouTube API search failed, falling back to yt-dlp")
                        await ctx.send(
                            "Using anonymous YouTube search (not connected to your account)"
                        )
                        query = f"ytsearch:{query}"
                        logger.debug(f"Using search query: {query}")

                # Check if the URL is a playlist
                is_playlist = "playlist" in query or "list=" in query
                logger.debug(f"Is playlist: {is_playlist}")

                if is_playlist:
                    logger.info(f"Processing playlist: {query}")
                    await ctx.send("Detected a playlist. Processing all songs...")
                    # Use the from_playlist method to get all songs from the playlist
                    logger.debug("Fetching playlist items")
                    song_infos, skipped_entries = await YTDLSource.from_playlist(
                        query,
                        loop=self.bot.loop,
                        stream=True,
                        volume=volumes[server_id],
                        create_source=False,
                    )

                    # Add all songs to the queue
                    logger.info(f"Adding {len(song_infos)} songs from playlist to queue")
                    for song_info in song_infos:
                        queues[server_id].append(song_info)
                        logger.debug(f"Added to queue: {song_info.title}")

                    # Inform about successfully added songs
                    await ctx.send(f"Added {len(song_infos)} songs from playlist to the queue.")

                    # Inform about any skipped videos
                    if skipped_entries:
                        logger.warning(f"{len(skipped_entries)} videos were skipped due to errors")
                        skipped_message = "The following videos were skipped due to errors:\n"
                        # Limit the number of skipped entries to show to avoid message length issues
                        max_entries_to_show = 5
                        if len(skipped_entries) > max_entries_to_show:
                            shown_entries = skipped_entries[:max_entries_to_show]
                            skipped_message += "\n".join(shown_entries)
                            skipped_message += (
                                f"\n...and {len(skipped_entries) - max_entries_to_show} more."
                            )
                        else:
                            skipped_message += "\n".join(skipped_entries)

                        await ctx.send(skipped_message)
                else:
                    # Use the server's volume setting for a single song
                    logger.info(f"Processing single song: {query}")
                    logger.debug(f"Using volume: {volumes[server_id]}")
                    try:
                        # Get song info without creating the source yet
                        song_info = await YTDLSource.from_url(
                            query,
                            loop=self.bot.loop,
                            stream=True,
                            volume=volumes[server_id],
                            create_source=False,
                        )

                        # Add the song info to the queue
                        queues[server_id].append(song_info)
                        logger.info(f"Added to queue: {song_info.title}")
                        await ctx.send(f"Added to queue: {song_info.title}")
                    except Exception as e:
                        logger.error(f"Error adding song to queue: {str(e)}")
                        await ctx.send(f"Could not add song to queue: {str(e)}")
                        return

                # If nothing is currently playing, start playing
                if not voice_channel.is_playing() and not voice_channel.is_paused():
                    logger.info("Nothing currently playing, starting playback")
                    await play_next(ctx, self.bot)

        except Exception as e:
            logger.error(f"Error in play command: {str(e)}", exc_info=True)
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="pause", help="This command pauses the song")
    async def pause(self, ctx):
        """Pause the currently playing song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server = ctx.message.guild
        logger.info(f"Pause command invoked by {ctx.author} in server {server.name}")

        voice_client = server.voice_client
        if voice_client is None:
            logger.warning(f"Bot not connected to voice channel in server {server.name}")
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            logger.info("Pausing playback")
            voice_client.pause()
        else:
            logger.warning("Nothing is currently playing, cannot pause")
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name="resume", help="Resumes the song")
    async def resume(self, ctx):
        """Resume a paused song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server = ctx.message.guild
        logger.info(f"Resume command invoked by {ctx.author} in server {server.name}")

        voice_client = server.voice_client
        if voice_client is None:
            logger.warning(f"Bot not connected to voice channel in server {server.name}")
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_paused():
            logger.info("Resuming playback")
            voice_client.resume()
        else:
            logger.warning("Nothing is paused, cannot resume")
            await ctx.send("The bot was not playing anything before this. Use !play command")

    @commands.command(name="stop", help="Stops the song")
    async def stop(self, ctx):
        """Stop the currently playing song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server = ctx.message.guild
        logger.info(f"Stop command invoked by {ctx.author} in server {server.name}")

        voice_client = server.voice_client
        if voice_client is None:
            logger.warning(f"Bot not connected to voice channel in server {server.name}")
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            logger.info("Stopping playback")
            voice_client.stop()
            # Ensure FFmpeg process is properly terminated
            logger.debug("Waiting for FFmpeg process to terminate")
            await asyncio.sleep(0.5)  # Give a moment for the process to terminate
        else:
            logger.warning("Nothing is currently playing, cannot stop")
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name="skip", help="Skips the current song")
    async def skip(self, ctx):
        """Skip the current song and play the next one in the queue.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server = ctx.message.guild
        logger.info(f"Skip command invoked by {ctx.author} in server {server.name}")

        voice_client = server.voice_client
        if voice_client is None:
            logger.warning(f"Bot not connected to voice channel in server {server.name}")
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            logger.info("Skipping current song")
            voice_client.stop()  # Stopping will trigger the after function which plays the next song
            # Ensure FFmpeg process is properly terminated
            logger.debug("Waiting for FFmpeg process to terminate")
            await asyncio.sleep(0.5)  # Give a moment for the process to terminate
            await ctx.send("Skipped the current song.")
        else:
            logger.warning("Nothing is currently playing, cannot skip")
            await ctx.send("The bot is not playing anything at the moment.")


async def setup(bot):
    """Add the PlaybackCommands cog to the bot.

    Args:
        bot: The Discord bot instance.

    Returns:
        None
    """
    logger.info("Setting up PlaybackCommands cog")
    await bot.add_cog(PlaybackCommands(bot))
    logger.success("PlaybackCommands cog has been added to the bot")
