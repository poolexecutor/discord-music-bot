import asyncio
from collections import deque

from discord.ext import commands

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

    @commands.command(name="play", help="To play a song (URL or search term)")
    async def play(self, ctx, *, query):
        """Play a song from a YouTube URL or search term.

        This command will:
        1. Search for the song if a search term is provided
        2. Add the song to the server's queue
        3. Start playing if nothing is currently playing

        Args:
            ctx: The command context.
            query: The YouTube URL or search term.

        Returns:
            None
        """
        try:
            server = ctx.message.guild
            server_id = server.id
            voice_channel = server.voice_client

            if not voice_channel:
                await ctx.send("Bot is not connected to a voice channel. Use !join first.")
                return

            # Initialize queue for this server if it doesn't exist
            if server_id not in queues:
                queues[server_id] = deque()

            # Initialize volume for this server if it doesn't exist
            if server_id not in volumes:
                volumes[server_id] = 0.5  # Default to 50%

            async with ctx.typing():
                # Check if the query is a URL or a search term
                if not query.startswith("https://"):
                    await ctx.send(f"Searching for: {query}...")

                    # Try to use authenticated YouTube API first
                    videos = await search_youtube(query)

                    if videos and len(videos) > 0:
                        # Use the first result from authenticated search
                        await ctx.send(f"Found: {videos[0]['title']} (using your YouTube account)")
                        query = videos[0]["url"]
                    else:
                        # Fall back to yt-dlp search if API search fails
                        await ctx.send(
                            "Using anonymous YouTube search (not connected to your account)"
                        )
                        query = f"ytsearch:{query}"

                # Use the server's volume setting
                player = await YTDLSource.from_url(
                    query, loop=self.bot.loop, stream=True, volume=volumes[server_id]
                )

                # Add the song to the queue
                queues[server_id].append(player)

                # If nothing is currently playing, start playing
                if not voice_channel.is_playing() and not voice_channel.is_paused():
                    await play_next(ctx, self.bot)
                else:
                    await ctx.send(f"Added to queue: {player.title}")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="pause", help="This command pauses the song")
    async def pause(self, ctx):
        """Pause the currently playing song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        voice_client = ctx.message.guild.voice_client
        if voice_client is None:
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name="resume", help="Resumes the song")
    async def resume(self, ctx):
        """Resume a paused song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        voice_client = ctx.message.guild.voice_client
        if voice_client is None:
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("The bot was not playing anything before this. Use !play command")

    @commands.command(name="stop", help="Stops the song")
    async def stop(self, ctx):
        """Stop the currently playing song.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        voice_client = ctx.message.guild.voice_client
        if voice_client is None:
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            voice_client.stop()
            # Ensure FFmpeg process is properly terminated
            await asyncio.sleep(0.5)  # Give a moment for the process to terminate
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name="skip", help="Skips the current song")
    async def skip(self, ctx):
        """Skip the current song and play the next one in the queue.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        voice_client = ctx.message.guild.voice_client
        if voice_client is None:
            await ctx.send("Bot is not connected to a voice channel.")
            return

        if voice_client.is_playing():
            voice_client.stop()  # Stopping will trigger the after function which plays the next song
            # Ensure FFmpeg process is properly terminated
            await asyncio.sleep(0.5)  # Give a moment for the process to terminate
            await ctx.send("Skipped the current song.")
        else:
            await ctx.send("The bot is not playing anything at the moment.")


def setup(bot):
    """Add the PlaybackCommands cog to the bot.

    Args:
        bot: The Discord bot instance.

    Returns:
        None
    """
    bot.add_cog(PlaybackCommands(bot))
