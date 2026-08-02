import requests

from config import YOUTUBE_API_KEY, YOUTUBE_REGION_CODE
from platforms.base import PlatformClient, TrendSource

VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeTrendSource(TrendSource):
    """Читает популярные видео через YouTube Data API v3 (нужен только API key)."""

    name = "youtube"

    def fetch_trends(self, limit: int = 10) -> list:
        if not YOUTUBE_API_KEY:
            raise RuntimeError("YOUTUBE_API_KEY не задан в .env")
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": YOUTUBE_REGION_CODE,
            "maxResults": limit,
            "videoCategoryId": "0",
            "key": YOUTUBE_API_KEY,
        }
        resp = requests.get(VIDEOS_URL, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "title": item["snippet"]["title"],
                "source": "youtube",
                "meta": {
                    "video_id": item["id"],
                    "channel": item["snippet"]["channelTitle"],
                    "tags": item["snippet"].get("tags", []),
                    "views": item.get("statistics", {}).get("viewCount"),
                },
            }
            for item in items
        ]


class YouTubeClient(PlatformClient):
    """Загрузка видео на YouTube (Shorts) требует OAuth-приложения (google-api-python-client).

    Настройка: создать проект в Google Cloud Console, включить YouTube Data API v3,
    получить OAuth client secrets, пройти согласие пользователя (consent flow),
    затем использовать videos.insert с resumable upload.
    """

    name = "youtube"

    def publish(self, content: dict) -> dict:
        raise NotImplementedError(
            "Загрузка видео на YouTube не настроена: нужен OAuth client (YOUTUBE_OAUTH_CLIENT_SECRETS_FILE) "
            "и интеграция google-api-python-client videos.insert."
        )

    def get_comments(self, post_id: str) -> list:
        raise NotImplementedError("Требуется OAuth-доступ к commentThreads.list")

    def reply_comment(self, comment_id: str, text: str) -> None:
        raise NotImplementedError("Требуется OAuth-доступ к comments.insert")

    def get_analytics(self, post_id: str) -> dict:
        raise NotImplementedError("Требуется YouTube Analytics API")
