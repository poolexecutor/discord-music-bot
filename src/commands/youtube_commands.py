import os

from discord.ext import commands

from src.config import TOKEN_PICKLE_PATH
from src.utils.youtube_api import authenticate_youtube


class YouTubeCommands(commands.Cog):
    """Commands for connecting to and managing YouTube account integration.

    This cog provides commands for connecting the bot to a user's YouTube account
    to enable personalized search results.
    """

    def __init__(self, bot):
        """Initialize the YouTubeCommands cog.

        Args:
            bot: The Discord bot instance.
        """
        self.bot = bot

    @commands.command(name="connect_youtube", help="Connect to your YouTube account")
    async def connect_youtube(self, ctx):
        """Connect or reconnect to a YouTube account.

        This command:
        1. Removes any existing authentication token
        2. Initiates the OAuth2 flow to authenticate with YouTube
        3. Stores the credentials for future use

        Args:
            ctx: The command context.

        Returns:
            None
        """
        await ctx.send("Attempting to connect to your YouTube account...")

        # Delete existing token to force re-authentication
        if os.path.exists(TOKEN_PICKLE_PATH):
            os.remove(TOKEN_PICKLE_PATH)
            await ctx.send("Removed existing YouTube authentication.")

        try:
            # Re-authenticate with YouTube
            authenticate_youtube()
            await ctx.send(
                "✅ Successfully connected to your YouTube account! Your searches will now use your account's preferences and history."
            )
        except Exception as e:
            await ctx.send(f"❌ Failed to connect to YouTube account: {str(e)}")
            await ctx.send("Make sure you've set up your YouTube API credentials in the .env file.")
            await ctx.send("The bot will continue to function using anonymous YouTube access.")


def setup(bot):
    """Add the YouTubeCommands cog to the bot.

    Args:
        bot: The Discord bot instance.

    Returns:
        None
    """
    bot.add_cog(YouTubeCommands(bot))
