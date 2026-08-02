from platforms.base import PlatformClient


class InstagramClient(PlatformClient):
    """Публикация через Instagram Graph API (Content Publishing).

    Требует: Instagram Business/Creator аккаунт, привязанный к Facebook Page,
    Facebook App с прохождением App Review для разрешений
    instagram_content_publish / instagram_manage_comments, долгоживущий
    access token. Пока INSTAGRAM_ACCESS_TOKEN/INSTAGRAM_BUSINESS_ACCOUNT_ID
    пусты, публикация недоступна.
    """

    name = "instagram"

    def publish(self, content: dict) -> dict:
        raise NotImplementedError(
            "Instagram Graph API не подключён: нужны INSTAGRAM_ACCESS_TOKEN и "
            "INSTAGRAM_BUSINESS_ACCOUNT_ID, а также пройденный Facebook App Review "
            "для instagram_content_publish."
        )

    def get_comments(self, post_id: str) -> list:
        raise NotImplementedError("Требуется разрешение instagram_manage_comments")

    def reply_comment(self, comment_id: str, text: str) -> None:
        raise NotImplementedError("Требуется разрешение instagram_manage_comments")

    def get_analytics(self, post_id: str) -> dict:
        raise NotImplementedError("Требуется Instagram Insights API")
