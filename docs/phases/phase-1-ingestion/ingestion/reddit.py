import logging
import requests
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def fetch_reddit_posts():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    subreddits = [
        "spotify",
        "SpotifyPlaylists", 
        "ifyoulikeblank",
        "musicsuggestions"
    ]
    
    all_posts = []
    
    for sub in subreddits:
        for sort in ["hot", "top"]:
            if sort == "top":
                url = f"https://www.reddit.com/r/{sub}/top.json?t=month&limit=100"
            else:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=100"
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                posts = response.json()["data"]["children"]
                
                for post in posts:
                    d = post["data"]
                    all_posts.append({
                        "source": "reddit",
                        "date": datetime.fromtimestamp(d["created_utc"], tz=timezone.utc).isoformat(),
                        "rating": None,
                        "title": d["title"],
                        "text": d["selftext"],
                        "score": d["score"],
                        "subreddit": d["subreddit"]
                    })
            except Exception as exc:
                logger.warning("Failed to fetch %s posts from r/%s: %s", sort, sub, exc)
            
            time.sleep(2)
    
    return all_posts

def fetch_reddit(since=None):
    return fetch_reddit_posts()
