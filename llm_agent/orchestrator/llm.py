"""Klient LLM. Wyłącznie DeepSeek (API zgodne z OpenAI). Bez fallbacku na inne modele."""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .config import Settings


class LLMError(RuntimeError):
    """Błąd wywołania DeepSeek (sieć, autoryzacja, limit, niepoprawna odpowiedź). Nie ma fallbacku."""


class ChatClient(Protocol):
    async def complete_json(self, system: str, user: str) -> dict[str, Any]: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(_FENCE.sub("", (text or "").strip()))
    except json.JSONDecodeError as e:
        raise LLMError(f"Odpowiedź DeepSeek nie jest poprawnym JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError("Odpowiedź DeepSeek nie jest obiektem JSON")
    return data


class DeepSeekClient:
    """Cienka nakładka na AsyncOpenAI wskazującą na api.deepseek.com."""

    def __init__(self, settings: Settings, client: Any | None = None):
        errs = settings.validate()
        if errs:
            raise LLMError("; ".join(errs))
        if client is None:
            if not settings.deepseek_api_key:
                raise LLMError("Brak DEEPSEEK_API_KEY")
            from openai import AsyncOpenAI  # import leniwy: testy nie wymagają sieci

            client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                timeout=settings.llm_timeout_s,
                max_retries=2,  # ponowienia transportowe do TEGO SAMEGO endpointu
            )
        self._client = client
        self._s = settings

    async def complete_json(self, system: str, user: str) -> dict[str, Any]:
        thinking = {"type": "enabled" if self._s.deepseek_thinking else "disabled"}
        try:
            resp = await self._client.chat.completions.create(
                model=self._s.deepseek_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                extra_body={"thinking": thinking},
            )
            content = resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001 — każdy błąd transportu/autoryzacji => LLMError, bez fallbacku
            raise LLMError(f"Wywołanie DeepSeek nie powiodło się: {e}") from e
        return parse_json_object(content)
