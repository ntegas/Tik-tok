import json

from agents.base import BaseAgent


class AnalyticsAgent(BaseAgent):
    """Превращает сырые метрики опубликованных постов в понятные выводы и рекомендации."""

    system_prompt = (
        "Ты — аналитик соцсетей. Тебе дают метрики нескольких постов (просмотры, лайки, "
        "комментарии, репосты, retention). Дай краткий вывод: что сработало, что нет, "
        "что попробовать в следующих постах. Отвечай СТРОГО JSON: "
        '{"summary": "...", "what_worked": ["..."], "what_to_try_next": ["..."]}'
    )

    def summarize(self, posts_metrics: list) -> dict:
        raw_response = self.ask(json.dumps(posts_metrics, ensure_ascii=False), max_tokens=800)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {"summary": raw_response, "what_worked": [], "what_to_try_next": []}
