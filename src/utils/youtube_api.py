import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from src.config import SCOPES, TOKEN_PICKLE_PATH, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET

# YouTube API client
youtube = None


def authenticate_youtube():
    """Authenticate with YouTube API and return the API client."""
    global youtube
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create client config from environment variables
            client_config = {
                "installed": {
                    "client_id": YOUTUBE_CLIENT_ID,
                    "client_secret": YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_PICKLE_PATH, "wb") as token:
            pickle.dump(creds, token)

    # Build the YouTube API service
    youtube = build("youtube", "v3", credentials=creds)
    return youtube


async def search_youtube(query, max_results=1):
    """Search YouTube using the authenticated API."""
    if not youtube:
        # If YouTube API authentication failed, return None
        logger.warning("YouTube API not authenticated, cannot search")
        return None

    try:
        # Call the search.list method to retrieve results matching the specified query term
        logger.debug(f"Searching YouTube for: {query} (max_results={max_results})")
        search_response = (
            youtube.search()
            .list(q=query, part="id,snippet", maxResults=max_results, type="video")
            .execute()
        )

        videos = []
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                video_id = search_result["id"]["videoId"]
                title = search_result["snippet"]["title"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                logger.debug(f"Found video: {title} ({url})")
                videos.append(
                    {
                        "id": video_id,
                        "title": title,
                        "url": url,
                    }
                )

        logger.info(f"Found {len(videos)} videos matching query: {query}")
        return videos
    except Exception as e:
        logger.error(f"Error searching YouTube API: {str(e)}")
        return None
