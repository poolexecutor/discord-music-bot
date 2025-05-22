import discord
from discord.ext import commands

from src.config import COMMAND_PREFIX, SSL_VERIFY, TOKEN, configure_ssl
from src.utils.youtube_api import authenticate_youtube


def main() -> None:
    """Initialize and run the Discord bot.

    This function:
    1. Configures SSL verification
    2. Sets up the bot with appropriate intents
    3. Registers event handlers
    4. Loads command extensions
    5. Starts the bot
    """
    # Configure SSL verification
    configure_ssl()

    # Set up the bot with command prefix
    intents = discord.Intents.default()
    intents.message_content = True

    # Configure SSL verification for discord.py
    if not SSL_VERIFY:
        # Use ssl=False parameter to disable SSL verification
        bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, ssl=False)
    else:
        bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

    # Load command extensions using setup_hook
    async def setup_hook() -> None:
        """Initialize the bot with extensions and other setup tasks.

        This method is automatically called by discord.py during bot initialization.
        """
        await bot.load_extension("src.commands.voice_commands")
        await bot.load_extension("src.commands.playback_commands")
        await bot.load_extension("src.commands.queue_commands")
        await bot.load_extension("src.commands.youtube_commands")

    # Assign the setup_hook method to the bot
    bot.setup_hook = setup_hook

    # Bot events
    @bot.event
    async def on_ready() -> None:
        """Event handler that runs when the bot has successfully connected to Discord.

        Attempts to authenticate with YouTube API.
        """
        if bot.user:
            print(f"{bot.user.name} has connected to Discord!")
        else:
            print("Bot has connected to Discord!")

        # Authenticate with YouTube API
        try:
            authenticate_youtube()
            print("Successfully authenticated with YouTube API!")
        except Exception as e:
            print(f"Failed to authenticate with YouTube API: {str(e)}")
            print("Bot will continue to function using yt-dlp for anonymous access.")

    # Run the bot
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
