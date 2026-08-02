import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from platforms.base import PlatformClient

API_URL = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient(PlatformClient):
    """Публикация постов в Telegram-канал/чат через Bot API (не требует app review)."""

    name = "telegram"

    def _call(self, method: str, **params):
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")
        url = API_URL.format(token=TELEGRAM_BOT_TOKEN, method=method)
        resp = requests.post(url, data=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
        return payload["result"]

    def publish(self, content: dict) -> dict:
        chat_id = content.get("chat_id", TELEGRAM_CHAT_ID)
        text = content["caption"]
        result = self._call("sendMessage", chat_id=chat_id, text=text)
        return {"post_id": str(result["message_id"]), "url": None}

    def get_comments(self, post_id: str) -> list:
        # Telegram Bot API не отдаёт комментарии к посту напрямую; для этого
        # нужен доступ к discussion group, привязанной к каналу, и getUpdates/webhook
        # на сообщения в этой группе с reply_to_message == post_id.
        raise NotImplementedError("Нужна привязанная discussion-группа + обработка апдейтов")

    def reply_comment(self, comment_id: str, text: str) -> None:
        chat_id = TELEGRAM_CHAT_ID
        self._call("sendMessage", chat_id=chat_id, text=text, reply_to_message_id=comment_id)

    def get_analytics(self, post_id: str) -> dict:
        raise NotImplementedError("Telegram Bot API не даёт статистику просмотров; нужен Telethon/MTProto")
