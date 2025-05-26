import discord
from discord.ext import commands
from loguru import logger

from src.config import (
    COMMAND_PREFIX,
    SSL_VERIFY,
    TOKEN,
    YOUTUBE_AUTH_ON_STARTUP,
    configure_ssl,
)
from src.utils.logger import setup_logger
from src.utils.youtube_api import authenticate_youtube


def main() -> None:
    """Initialize and run the Discord bot.

    This function:
    1. Sets up logging
    2. Configures SSL verification
    3. Sets up the bot with appropriate intents
    4. Registers event handlers
    5. Loads command extensions
    6. Starts the bot
    """
    # Set up logging
    setup_logger()

    # Configure SSL verification
    configure_ssl()

    # Set up the bot with command prefix
    intents = discord.Intents.default()
    intents.message_content = True

    # Configure SSL verification for discord.py
    if not SSL_VERIFY:
        # Use ssl=False parameter to disable SSL verification
        logger.warning(
            "SSL certificate verification is disabled. This is not recommended for production use."
        )
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
        logger.debug("All extensions loaded")

    # Assign the setup_hook method to the bot
    bot.setup_hook = setup_hook

    # Bot events
    @bot.event
    async def on_ready() -> None:
        """Event handler that runs when the bot has successfully connected to Discord.

        Attempts to authenticate with YouTube API if YOUTUBE_AUTH_ON_STARTUP is True.
        """
        if bot.user:
            logger.info(f"{bot.user.name} has connected to Discord!")
        else:
            logger.info("Bot has connected to Discord!")

        # Authenticate with YouTube API only if explicitly enabled
        if YOUTUBE_AUTH_ON_STARTUP:
            logger.info("YouTube authentication on startup is enabled")
            try:
                authenticate_youtube()
                logger.info("Successfully authenticated with YouTube API!")
            except Exception as e:
                logger.error(f"Failed to authenticate with YouTube API: {str(e)}")
                logger.info("Bot will continue to function using yt-dlp for anonymous access.")
        else:
            logger.info("YouTube authentication on startup is disabled")
            logger.info(
                "Use the !connect_youtube command to authenticate with YouTube API when needed"
            )

    # Run the bot
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
