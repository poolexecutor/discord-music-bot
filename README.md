# Discord Music Bot

A Discord bot that can connect to YouTube, join voice channels, and play music.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.5.2-blue?logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Latest-green?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- Join and leave voice channels
- Play music from YouTube URLs or search terms
- Connect to your personal YouTube account for personalized search results
- Queue system for multiple songs
- Pause, resume, and stop music playback
- Adjustable volume control
- Simple command interface

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- Discord Bot Token

## Setup

You can set up the bot either directly on your system or using Docker.

### Option 1: Direct Installation

#### 1. Install FFmpeg

#### Windows
Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH.

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "TOKEN" section, click "Copy" to copy your bot token
5. Enable the following Privileged Gateway Intents:
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT
6. Go to the "OAuth2" tab, then "URL Generator"
7. Select the following scopes: `bot`, `applications.commands`
8. Select the following bot permissions:
   - Send Messages
   - Connect
   - Speak
   - Use Voice Activity
9. Copy the generated URL and open it in your browser to add the bot to your server

### 3. Set Up YouTube API (Optional, for connecting to your YouTube account)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3:
   - In the sidebar, click on "APIs & Services" > "Library"
   - Search for "YouTube Data API v3" and enable it
4. Create OAuth credentials:
   - In the sidebar, click on "APIs & Services" > "Credentials"
   - Click "Create Credentials" and select "OAuth client ID"
   - Select "Desktop app" as the application type and give it a name
   - Click "Create"
5. Download the credentials:
   - After creating the credentials, click the download button (JSON)
6. Get your API Key:
   - In the Credentials page, click "Create Credentials" again and select "API Key"
   - Copy the API key
7. Edit the `.env` file and add your YouTube API credentials:
   ```
   YOUTUBE_CLIENT_ID=your_client_id_here
   YOUTUBE_CLIENT_SECRET=your_client_secret_here
   YOUTUBE_API_KEY=your_api_key_here
   ```

### 4. Configure the Bot

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Edit the `.env` file and add your actual Discord bot token to the `DISCORD_TOKEN=` line
   - Do not include any quotes around the token

### 5. Run the Bot

```bash
python main.py
```

### Option 2: Docker Installation

Using Docker is the easiest way to deploy the bot, as it handles all dependencies and environment setup automatically.

#### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

#### 2. Setup

1. Clone this repository
2. Create a `data` directory for persistent storage:
   ```bash
   mkdir -p data
   ```
3. Make sure your `.env` file is properly configured with your Discord token and YouTube API credentials

#### 3. Build and Run

**Option A: Using the convenience script**

```bash
# Make the script executable (first time only)
chmod +x 1_docker_up.sh

# Run the script
./1_docker_up.sh
```

**Option B: Manual commands**

```bash
# Navigate to the docker directory
cd docker

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The bot will automatically restart if it crashes or if the server reboots, unless you explicitly stop it with `docker-compose down`.

## Commands

- `!join` - Bot joins your current voice channel
- `!leave` - Bot leaves the voice channel
- `!play [youtube_url or search terms]` - Plays audio from YouTube URL or searches for the terms
- `!pause` - Pauses the currently playing audio
- `!resume` - Resumes paused audio
- `!stop` - Stops playing audio
- `!skip` - Skips the current song and plays the next one in the queue
- `!queue` - Shows the current queue of songs
- `!clear` - Clears all songs from the queue
- `!volume [0-100]` - Shows the current volume or sets it to the specified percentage
- `!connect_youtube` - Connect to your YouTube account for personalized search results

## Example Usage

1. Join a voice channel in Discord
2. Type `!join` to make the bot join your channel
3. (Optional) Connect to your YouTube account:
   - Make sure you've set up YouTube API credentials in the `.env` file
   - Type `!connect_youtube` to start the authentication process
   - A browser window will open asking you to sign in to your Google account
   - After signing in, grant the requested permissions
   - The bot will confirm when you're successfully connected
4. Play music using one of these methods:
   - Direct URL: `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - Search terms: `!play never gonna give you up`
   - If connected to your YouTube account, searches will use your account's preferences
5. Add more songs to the queue:
   - `!play another song name`
   - The bot will automatically play the next song when the current one finishes
6. Manage your queue:
   - `!queue` to see what songs are in the queue
   - `!skip` to skip to the next song
   - `!clear` to remove all songs from the queue
7. Control playback and volume:
   - `!pause`, `!resume`, and `!stop` to control playback
   - `!volume` to check the current volume level
   - `!volume 75` to set the volume to 75%
8. Type `!leave` when you're done

## Troubleshooting

- If you encounter errors related to FFmpeg, make sure it's properly installed and accessible in your PATH
- If you see messages like "ffmpeg process has not terminated. Waiting to terminate..." or "ffmpeg process should have terminated with a return code of -9":
  - This is usually due to FFmpeg processes not being properly terminated
  - The bot includes improved error handling to address this issue
  - If you still encounter this issue, try restarting the bot
  - In some cases, you may need to manually kill FFmpeg processes on your system
- If the bot doesn't respond or you see an error like "Improper token has been passed":
  - Check that your Discord token is correct in the `.env` file
  - Make sure you've copied the entire token from the Discord Developer Portal
  - Verify that the token hasn't been revoked or regenerated in the Discord Developer Portal
- Make sure the bot has the necessary permissions in your Discord server
- If you encounter YouTube signature extraction errors (like `Could not find JS function 'decodeURIComponent'`):
  - This bot uses yt-dlp, a more actively maintained fork of youtube-dl, to handle YouTube video extraction
  - If you still encounter issues, try updating yt-dlp to the latest version:
    ```bash
    pip install --upgrade yt-dlp
    ```
- If you encounter SSL certificate verification errors (like `SSLCertVerificationError: certificate verify failed`):
  - Add `SSL_VERIFY=False` to your `.env` file (this is already set by default)
  - This will disable SSL verification for both the global SSL context and for discord.py using the built-in ssl=False parameter
  - Note that disabling SSL verification is not recommended for production use due to security concerns
  - A better solution is to install proper SSL certificates on your system
- For YouTube account connection issues:
  - Verify that your YouTube API credentials are correct in the `.env` file
  - Make sure you've enabled the YouTube Data API v3 in your Google Cloud Console
  - If authentication fails, try running the `!connect_youtube` command again
  - If you get quota exceeded errors, you may need to wait until your quota resets or request an increase
  - The bot will still work without YouTube API credentials, but will use anonymous YouTube access

## Project Structure

The project is organized into the following directories:

- `src/`: Contains the main bot code
  - `commands/`: Command handlers for the bot
  - `player/`: Music player functionality
  - `utils/`: Utility functions and API clients
- `docker/`: Docker-related files for containerization
- `data/`: Persistent data storage (created at runtime)
- `requirements/`: Contains dependency files
  - `prod.txt`: Production dependencies
  - `dev.txt`: Development dependencies

## Development

### Code Quality Tools

This project uses several code quality tools to maintain consistent style and catch potential issues:

1. **Black**: Code formatter that enforces a consistent style
2. **Ruff**: Fast Python linter that combines multiple linting tools
3. **MyPy**: Static type checker for Python

These tools are configured in `pyproject.toml` and can be run using the provided script:

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run all linting tools in check mode (no changes)
./src/lint.py --check

# Run all linting tools and fix issues where possible
./src/lint.py --fix

# Install missing linting tools if needed
./src/lint.py --install
```

### Type Annotations

The codebase uses type annotations to improve code quality and enable static type checking with MyPy. This helps catch type-related errors before runtime and improves code documentation.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
