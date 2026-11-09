import json
import re
from typing import Any
import httpx

from .config import settings


class DeepSeekClient:
    """Lazy HTTP client: MOCK_MODE=true 时不会触发任何外部模型调用。"""

    async def chat(self, system: str, user: str, json_mode: bool = False, temperature: float = 0.2) -> str:
        if settings.mock_mode:
            raise RuntimeError("DeepSeekClient should not be called in MOCK_MODE")
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required when MOCK_MODE=false")

        payload: dict[str, Any] = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    async def json(self, system: str, user: str) -> dict[str, Any]:
        text = await self.chat(system, user, json_mode=True, temperature=0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                raise
            return json.loads(match.group(0))


llm = DeepSeekClient()
