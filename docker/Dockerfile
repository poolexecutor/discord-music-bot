FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements/prod.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY main.py .
COPY src/ ./src/
# Don't copy .env file - it will be mounted as a volume

# Create a volume for persistent data
VOLUME /app/data

# Modify the script to use the data directory for token.pickle
ENV TOKEN_PICKLE_PATH=/app/data/token.pickle

# Run the bot
CMD ["python", "main.py"]
