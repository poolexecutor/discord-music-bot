from discord.ext import commands

from src.config import DEFAULT_VOLUME
from src.player.queue_manager import queues, volumes


class QueueCommands(commands.Cog):
    """Commands for managing the music queue and volume.

    This cog provides commands for viewing and clearing the queue,
    as well as adjusting the playback volume.
    """

    def __init__(self, bot):
        """Initialize the QueueCommands cog.

        Args:
            bot: The Discord bot instance.
        """
        self.bot = bot

    @commands.command(name="queue", help="Shows the current queue")
    async def queue_info(self, ctx):
        """Display the current queue of songs.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server_id = ctx.guild.id
        if server_id in queues and queues[server_id]:
            queue_list = list(queues[server_id])
            response = "**Current Queue:**\n"
            for i, song in enumerate(queue_list, 1):
                response += f"{i}. {song.title}\n"
            await ctx.send(response)
        else:
            await ctx.send("The queue is empty.")

    @commands.command(name="clear", help="Clears the queue")
    async def clear_queue(self, ctx):
        """Clear all songs from the queue.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        server_id = ctx.guild.id
        if server_id in queues:
            queues[server_id].clear()
            await ctx.send("Queue cleared.")
        else:
            await ctx.send("The queue is already empty.")

    @commands.command(name="volume", help="Shows or sets the volume (0-100)")
    async def volume(self, ctx, volume_percent: int | None = None):
        """Show or set the playback volume.

        If no volume is specified, shows the current volume.
        Otherwise, sets the volume to the specified percentage.

        Args:
            ctx: The command context.
            volume_percent: The volume percentage (0-100), or None to show current volume.

        Returns:
            None
        """
        server_id = ctx.guild.id
        voice_client = ctx.guild.voice_client

        # Initialize volume for this server if it doesn't exist
        if server_id not in volumes:
            volumes[server_id] = DEFAULT_VOLUME  # Default to 50%

        # If no volume specified, show current volume
        if volume_percent is None:
            current_percent = int(volumes[server_id] * 100)
            await ctx.send(f"Current volume: {current_percent}%")
            return

        # Validate volume input
        if not 0 <= volume_percent <= 100:
            await ctx.send("Volume must be between 0 and 100")
            return

        # Convert percentage to float (0.0 to 1.0)
        new_volume = volume_percent / 100

        # Store the new volume
        volumes[server_id] = new_volume

        # Update the volume of the currently playing source if there is one
        if voice_client and voice_client.source:
            voice_client.source.volume = new_volume

        await ctx.send(f"Volume set to {volume_percent}%")


async def setup(bot):
    """Add the QueueCommands cog to the bot.

    Args:
        bot: The Discord bot instance.

    Returns:
        None
    """
    await bot.add_cog(QueueCommands(bot))
