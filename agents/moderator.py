import json

from agents.base import BaseAgent


class ModeratorAgent(BaseAgent):
    """Проверяет черновики постов перед публикацией и разбирает входящие
    комментарии: решает, отвечать ли, банить/скрывать, или пропустить."""

    review_system_prompt = (
        "Ты — модератор соцсетей. Проверь черновик поста на: нарушение правил платформ "
        "(разжигание ненависти, спам, обман, авторские права), соответствие бренду, риск теневого "
        "бана. Отвечай СТРОГО JSON: "
        '{"approved": true/false, "reason": "...", "fixes": ["что поправить, если approved=false"]}.'
    )

    comment_system_prompt = (
        "Ты — модератор комментариев. Тебе дают комментарий под постом. Классифицируй и, если уместно, "
        "предложи ответ от имени аккаунта. Отвечай СТРОГО JSON: "
        '{"action": "reply" | "ignore" | "hide", "reason": "...", "suggested_reply": "..."}'
    )

    def review_post(self, draft: dict) -> dict:
        self.system_prompt = self.review_system_prompt
        raw_response = self.ask(json.dumps(draft, ensure_ascii=False), max_tokens=600)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {"approved": False, "reason": raw_response, "fixes": []}

    def triage_comment(self, comment_text: str, post_context: str = "") -> dict:
        self.system_prompt = self.comment_system_prompt
        user_message = f"Пост: {post_context}\nКомментарий: {comment_text}"
        raw_response = self.ask(user_message, max_tokens=400)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {"action": "ignore", "reason": raw_response, "suggested_reply": ""}
