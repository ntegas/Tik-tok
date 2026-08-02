"""Общие интерфейсы, которым следуют все платформенные клиенты.

Публикация в TikTok/Instagram требует одобренного доступа к их API
(TikTok Content Posting API, Instagram Graph API — оба выдаются только
верифицированным приложениям/бизнес-аккаунтам). Пока такого доступа нет,
соответствующие клиенты реализуют интерфейс, но публикация выбрасывает
NotImplementedError с пояснением, что нужно для запуска.
"""


class PlatformClient:
    name = "base"

    def publish(self, content: dict) -> dict:
        """Публикует контент, возвращает {"post_id": ..., "url": ...}."""
        raise NotImplementedError

    def get_comments(self, post_id: str) -> list:
        raise NotImplementedError

    def reply_comment(self, comment_id: str, text: str) -> None:
        raise NotImplementedError

    def get_analytics(self, post_id: str) -> dict:
        raise NotImplementedError


class TrendSource:
    name = "base"

    def fetch_trends(self, limit: int = 10) -> list:
        """Возвращает список трендов: [{"title": ..., "source": ..., "meta": {...}}, ...]"""
        raise NotImplementedError
