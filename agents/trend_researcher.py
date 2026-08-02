import json

from agents.base import BaseAgent


class TrendResearcherAgent(BaseAgent):
    """Берёт сырой список трендов из TrendSource и отбирает те, что стоит повторить,
    под конкретную нишу/аккаунт."""

    system_prompt = (
        "Ты — агент-исследователь трендов для соцсетей (TikTok, Instagram, YouTube Shorts). "
        "Тебе дают нишу аккаунта и список сырых трендов (заголовки видео, хэштеги, звуки). "
        "Отбери до 5 трендов, которые реально стоит адаптировать под эту нишу, и для каждого "
        "коротко объясни, как его повторить/адаптировать. Отвечай СТРОГО в формате JSON-массива "
        'вида [{"trend": "...", "why": "...", "how_to_adapt": "..."}], без текста вне JSON.'
    )

    def select_trends(self, niche: str, raw_trends: list) -> list:
        if not raw_trends:
            return []
        user_message = (
            f"Ниша аккаунта: {niche}\n\n"
            f"Сырые тренды:\n{json.dumps(raw_trends, ensure_ascii=False, indent=2)}"
        )
        raw_response = self.ask(user_message, max_tokens=1500)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return [{"trend": raw_response, "why": "", "how_to_adapt": ""}]
