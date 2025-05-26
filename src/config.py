import os
import ssl

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
TOKEN: str = os.getenv("DISCORD_TOKEN", "")  # Default to empty string if not set
COMMAND_PREFIX = "!"
DEFAULT_VOLUME = 0.05

# Logging configuration
VERBOSE_MODE = os.getenv("VERBOSE_MODE", "False").lower() == "true"

# YouTube API configuration
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# YouTube cookies file path (for accessing age-restricted or private videos)
COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", None)

# Get token.pickle path from environment variable or use default
TOKEN_PICKLE_PATH = os.getenv("TOKEN_PICKLE_PATH", "token.pickle")

# SSL verification setting (set to 'False' to disable SSL verification if you're having certificate issues)
SSL_VERIFY = os.getenv("SSL_VERIFY", "True").lower() != "false"

# YouTube authentication on startup setting (set to 'True' to enable authentication on startup)
YOUTUBE_AUTH_ON_STARTUP = os.getenv("YOUTUBE_AUTH_ON_STARTUP", "False").lower() == "true"


# Configure SSL verification
def configure_ssl():
    """Configure SSL verification based on the SSL_VERIFY setting.

    If SSL_VERIFY is False, this function disables SSL certificate verification
    by modifying the default HTTPS context. This is useful for development or
    in environments with SSL certificate issues, but should be avoided in production.
    """
    if not SSL_VERIFY:
        # We don't use logger here because it might not be initialized yet
        # The actual warning is logged in bot.py after logger initialization
        ssl._create_default_https_context = ssl._create_unverified_context
