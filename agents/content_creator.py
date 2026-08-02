import json

from agents.base import BaseAgent


class ContentCreatorAgent(BaseAgent):
    """Превращает выбранный тренд в готовый черновик поста: подпись, хэштеги,
    покадровый сценарий (для фазы 2 — полноценного монтажа видео)."""

    system_prompt = (
        "Ты — контент-креатор и режиссёр коротких видео для соцсетей. По тренду и нише "
        "придумай черновик поста. Отвечай СТРОГО в формате JSON-объекта: "
        '{"caption": "подпись с эмодзи", "hashtags": ["#..."], '
        '"shot_list": ["кадр 1: ...", "кадр 2: ..."], "hook": "первые 2 секунды, чтобы удержать зрителя"}. '
        "Без текста вне JSON."
    )

    def draft_post(self, niche: str, trend: dict) -> dict:
        user_message = (
            f"Ниша аккаунта: {niche}\n"
            f"Тренд: {json.dumps(trend, ensure_ascii=False)}"
        )
        raw_response = self.ask(user_message, max_tokens=1200)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {"caption": raw_response, "hashtags": [], "shot_list": [], "hook": ""}
