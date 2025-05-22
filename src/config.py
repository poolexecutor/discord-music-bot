import os
import ssl

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
TOKEN: str = os.getenv("DISCORD_TOKEN", "")  # Default to empty string if not set
COMMAND_PREFIX = "!"

# YouTube API configuration
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Get token.pickle path from environment variable or use default
TOKEN_PICKLE_PATH = os.getenv("TOKEN_PICKLE_PATH", "token.pickle")

# SSL verification setting (set to 'False' to disable SSL verification if you're having certificate issues)
SSL_VERIFY = os.getenv("SSL_VERIFY", "True").lower() != "false"


# Configure SSL verification
def configure_ssl():
    """Configure SSL verification based on the SSL_VERIFY setting.

    If SSL_VERIFY is False, this function disables SSL certificate verification
    by modifying the default HTTPS context. This is useful for development or
    in environments with SSL certificate issues, but should be avoided in production.
    """
    if not SSL_VERIFY:
        print(
            "Warning: SSL certificate verification is disabled. This is not recommended for production use."
        )
        ssl._create_default_https_context = ssl._create_unverified_context
