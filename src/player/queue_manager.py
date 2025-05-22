import asyncio
from collections import deque

# Music queue for each server
queues: dict[int, deque] = {}

# Volume levels for each server (default: 50%)
volumes: dict[int, float] = {}


async def play_next(ctx, bot):
    """Play the next song in the queue.

    This function:
    1. Gets the next song from the server's queue
    2. Plays it using the voice client
    3. Sets up a callback for when the song finishes

    Args:
        ctx: The command context.
        bot: The Discord bot instance.

    Returns:
        None
    """
    server_id = ctx.guild.id
    if server_id in queues and queues[server_id]:
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected():
            # Get the next song from the queue
            next_song = queues[server_id].popleft()

            # Play the next song
            voice_client.play(next_song, after=lambda e: handle_playback_completion(ctx, e, bot))

            await ctx.send(f"Now playing: {next_song.title}")
    else:
        # No more songs in the queue
        await ctx.send("Queue is empty. Add more songs with !play or !add")


def handle_playback_completion(ctx, error, bot):
    """Handle completion of song playback, including errors.

    This function is called when a song finishes playing or encounters an error.
    It will play the next song in the queue or clean up the voice client if there's an error.

    Args:
        ctx: The command context.
        error: The error that occurred, if any.
        bot: The Discord bot instance.

    Returns:
        None
    """
    if error:
        print(f"Player error: {error}")

    # Use run_coroutine_threadsafe to call play_next in the bot's event loop
    future = asyncio.run_coroutine_threadsafe(play_next(ctx, bot), bot.loop)
    try:
        future.result()
    except Exception as e:
        print(f"Error playing next song: {e}")
        # Try to ensure the voice client is properly cleaned up
        asyncio.run_coroutine_threadsafe(cleanup_voice_client(ctx), bot.loop)


async def cleanup_voice_client(ctx):
    """Ensure voice client is properly cleaned up.

    This function stops any playing audio and disconnects the voice client.
    It's used to clean up resources when there's an error or when the bot is shutting down.

    Args:
        ctx: The command context.

    Returns:
        None
    """
    try:
        voice_client = ctx.guild.voice_client
        if voice_client:
            if voice_client.is_playing():
                voice_client.stop()
            if voice_client.is_connected():
                await voice_client.disconnect()
    except Exception as e:
        print(f"Error cleaning up voice client: {e}")
