from discord.ext import commands


class VoiceCommands(commands.Cog):
    """Commands for managing the bot's voice channel connection.

    This cog provides commands for joining and leaving voice channels.
    """

    def __init__(self, bot):
        """Initialize the VoiceCommands cog.

        Args:
            bot: The Discord bot instance.
        """
        self.bot = bot

    @commands.command(name="join", help="Tells the bot to join the voice channel")
    async def join(self, ctx):
        """Join the voice channel that the user is currently in.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        if not ctx.message.author.voice:
            await ctx.send(f"{ctx.message.author.name} is not connected to a voice channel")
            return

        channel = ctx.message.author.voice.channel
        await channel.connect()

    @commands.command(name="leave", help="To make the bot leave the voice channel")
    async def leave(self, ctx):
        """Leave the current voice channel.

        Args:
            ctx: The command context.

        Returns:
            None
        """
        voice_client = ctx.message.guild.voice_client
        if voice_client is None:
            await ctx.send("The bot is not connected to a voice channel.")
            return

        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")


def setup(bot):
    """Add the VoiceCommands cog to the bot.

    Args:
        bot: The Discord bot instance.

    Returns:
        None
    """
    bot.add_cog(VoiceCommands(bot))
