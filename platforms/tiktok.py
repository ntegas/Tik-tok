from platforms.base import PlatformClient


class TikTokClient(PlatformClient):
    """Публикация видео через TikTok Content Posting API.

    Требует: регистрацию приложения на developers.tiktok.com, прохождение
    review для scope video.publish, OAuth2-токен пользователя/бизнес-аккаунта.
    Пока эти шаги не пройдены (TIKTOK_CLIENT_KEY/SECRET/ACCESS_TOKEN пусты),
    методы явно сообщают, чего не хватает, вместо тихого no-op.
    """

    name = "tiktok"

    def publish(self, content: dict) -> dict:
        raise NotImplementedError(
            "TikTok Content Posting API не подключён: нужны TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET "
            "и TIKTOK_ACCESS_TOKEN, полученные после регистрации приложения и прохождения review "
            "на developers.tiktok.com (scope video.publish)."
        )

    def get_comments(self, post_id: str) -> list:
        raise NotImplementedError("Требуется scope video.list/comment в TikTok API")

    def reply_comment(self, comment_id: str, text: str) -> None:
        raise NotImplementedError("TikTok API v2 не предоставляет публичный endpoint для ответа на комментарии")

    def get_analytics(self, post_id: str) -> dict:
        raise NotImplementedError("Требуется TikTok Display API / Business API для метрик")
