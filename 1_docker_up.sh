#!/bin/bash

# Discord Music Bot - Docker startup script
# This script builds and starts the Discord Music Bot Docker container

# Set script to exit on error
set -e

echo "=== Discord Music Bot - Docker Startup ==="
echo "Starting Docker container setup..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create a .env file with your Discord token and YouTube API credentials."
    echo "Example:"
    echo "DISCORD_TOKEN=your_discord_bot_token_here"
    echo "YOUTUBE_CLIENT_ID=your_client_id_here"
    echo "YOUTUBE_CLIENT_SECRET=your_client_secret_here"
    echo "YOUTUBE_API_KEY=your_api_key_here"
    echo "SSL_VERIFY=False"
    echo "VERBOSE_MODE=False"
    echo "YOUTUBE_AUTH_ON_STARTUP=False"
    exit 1
fi

# Create data directory if it doesn't exist
echo "Checking if data directory exists..."
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
    echo "Data directory created."
else
    echo "Data directory already exists."
fi

# Navigate to the docker directory
echo "Navigating to docker directory..."
cd docker

# Build and start the container
echo "Building and starting the Docker container..."
docker-compose stop
docker-compose up -d --build

# Check if container started successfully
if [ $? -eq 0 ]; then
    echo "Container started successfully!"
    echo ""
    echo "=== Container Information ==="
    echo "Container name: discord-music-bot"
    echo "To view logs: docker-compose logs -f"
    echo "To stop the container: docker-compose down"
    echo ""
    echo "The bot should now be running and connected to Discord."
    echo "Use the commands listed in the README.md to interact with the bot."

    # Return to the original directory
    cd ..
else
    echo "Error: Failed to start the container. Check the logs for more information."
    # Return to the original directory even if there was an error
    cd ..
    exit 1
fi

exit 0
