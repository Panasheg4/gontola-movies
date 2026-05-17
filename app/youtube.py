import os
import requests
from datetime import datetime, timedelta

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Simple in-memory cache
_cache = {}

def get_cached(key, fetch_fn, minutes=60):
    """
    Returns cached data if fresh.
    Otherwise fetches fresh data and caches it.
    """
    now = datetime.now()
    if key in _cache:
        data, expires = _cache[key]
        if now < expires:
            return data

    # Cache expired or missing — fetch fresh
    data = fetch_fn()
    _cache[key] = (data, now + timedelta(minutes=minutes))
    return data

def get_channel_stats():
    """Fetch live channel statistics."""
    def fetch():
        try:
            response = requests.get(
                f"{BASE_URL}/channels",
                params={
                    "part": "snippet,statistics",
                    "id": YOUTUBE_CHANNEL_ID,
                    "key": YOUTUBE_API_KEY
                },
                timeout=5
            )
            data = response.json()
            if "error" in data or not data.get("items"):
                return get_fallback_stats()

            channel = data["items"][0]
            stats = channel["statistics"]
            snippet = channel["snippet"]

            return {
                "name": snippet["title"],
                "description": snippet["description"],
                "subscribers": int(
                    stats.get("subscriberCount", 0)
                ),
                "views": int(stats.get("viewCount", 0)),
                "videos": int(stats.get("videoCount", 0)),
                "thumbnail": snippet["thumbnails"]["high"]["url"]
            }
        except Exception as e:
            print(f"YouTube channel error: {e}")
            return get_fallback_stats()

    return get_cached("channel_stats", fetch, minutes=60)

def get_fallback_stats():
    """Fallback if API fails."""
    return {
        "name": "Gontola Movies",
        "description": "Your home for everything movies.",
        "subscribers": 3860,
        "views": 1774519,
        "videos": 139,
        "thumbnail": ""
    }

def get_latest_videos(max_results=10):
    """Fetch latest videos from channel."""
    def fetch():
        try:
            response = requests.get(
                f"{BASE_URL}/search",
                params={
                    "part": "snippet",
                    "channelId": YOUTUBE_CHANNEL_ID,
                    "maxResults": max_results,
                    "order": "date",
                    "type": "video",
                    "key": YOUTUBE_API_KEY
                },
                timeout=5
            )
            data = response.json()
            if "error" in data:
                return []

            videos = []
            for item in data.get("items", []):
                snippet = item["snippet"]
                video_id = item["id"]["videoId"]

                # Clean title — remove hashtags
                title = snippet["title"]
                clean_title = " ".join(
                    word for word in title.split()
                    if not word.startswith("#")
                ).strip()

                videos.append({
                    "id": video_id,
                    "title": clean_title,
                    "full_title": title,
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "published": snippet["publishedAt"][:10],
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "description": snippet.get("description", "")[:100]
                })
            return videos

        except Exception as e:
            print(f"YouTube videos error: {e}")
            return []

    return get_cached("latest_videos", fetch, minutes=60)

def get_shorts(max_results=10):
    """
    Fetch latest shorts.
    Shorts are videos under 60 seconds
    but YouTube API doesn't filter by duration in search.
    We fetch latest videos and they are mostly shorts
    for your channel.
    """
    def fetch():
        try:
            response = requests.get(
                f"{BASE_URL}/search",
                params={
                    "part": "snippet",
                    "channelId": YOUTUBE_CHANNEL_ID,
                    "maxResults": max_results,
                    "order": "date",
                    "type": "video",
                    "videoDuration": "short",
                    "key": YOUTUBE_API_KEY
                },
                timeout=5
            )
            data = response.json()
            if "error" in data:
                return []

            shorts = []
            for item in data.get("items", []):
                snippet = item["snippet"]
                video_id = item["id"]["videoId"]

                title = snippet["title"]
                clean_title = " ".join(
                    word for word in title.split()
                    if not word.startswith("#")
                ).strip()

                shorts.append({
                    "id": video_id,
                    "title": clean_title,
                    "full_title": title,
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "published": snippet["publishedAt"][:10],
                    "url": f"https://youtube.com/shorts/{video_id}",
                    "embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "description": snippet.get(
                        "description", ""
                    )[:100]
                })
            return shorts

        except Exception as e:
            print(f"YouTube shorts error: {e}")
            return []

    return get_cached("shorts", fetch, minutes=60)

def format_number(num):
    """Format large numbers nicely."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)