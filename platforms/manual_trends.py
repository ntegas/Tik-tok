import json
import os

from config import MANUAL_TRENDS_FILE
from platforms.base import TrendSource

_TEMPLATE = [
    {"title": "Пример тренда — заполни data/manual_trends.json вручную", "source": "manual", "meta": {}}
]


class ManualTrendSource(TrendSource):
    """Заглушка-источник трендов для TikTok/Instagram, пока нет доступа к их API трендов.

    Официальные API трендов TikTok (Research API) и Instagram недоступны без
    партнёрского/академического доступа. До получения доступа тренды заносятся
    вручную в data/manual_trends.json (например, скопированы из вкладки
    "В тренде" в приложении) и подхватываются этим источником.
    """

    name = "manual"

    def __init__(self, platform: str):
        self.platform = platform

    def fetch_trends(self, limit: int = 10) -> list:
        if not os.path.exists(MANUAL_TRENDS_FILE):
            os.makedirs(os.path.dirname(MANUAL_TRENDS_FILE), exist_ok=True)
            with open(MANUAL_TRENDS_FILE, "w", encoding="utf-8") as f:
                json.dump({"tiktok": _TEMPLATE, "instagram": _TEMPLATE}, f, ensure_ascii=False, indent=2)

        with open(MANUAL_TRENDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(self.platform, [])[:limit]
