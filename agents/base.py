import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


class BaseAgent:
    """Общий предок для LLM-агентов: хранит системный промпт и умеет звать Claude."""

    system_prompt = "You are a helpful assistant."

    def __init__(self, model: str = ANTHROPIC_MODEL):
        self.model = model
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def ask(self, user_message: str, max_tokens: int = 1024) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
