"""Ograniczone czasowo powiadomienie HTTP WCSS -> backend."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

import httpx

from .config import Settings

log = logging.getLogger("orchestrator.callback")
Sleep = Callable[[float], Awaitable[None]]


async def notify_backend(
    request_id: str,
    result: dict[str, Any],
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    sleep: Sleep = asyncio.sleep,
) -> bool:
    """Wyślij callback z ograniczoną liczbą prób i całkowitym budżetem czasu.

    Brak URL oznacza świadomie wyłączony callback. Błąd callbacku nie zmienia
    wyniku pipeline'u: response JSON i audio pozostają na WCSS do odzyskania.
    """
    if not settings.callback_url:
        log.warning("callback wyłączony dla requestu %s: brak callback.url", request_id)
        return False
    if not settings.callback_token:
        log.error("callback odrzucony dla requestu %s: brak callback.token", request_id)
        return False

    headers = {"Authorization": f"Bearer {settings.callback_token}"}
    payload = {
        "request_id": request_id,
        "execution_code": result.get("execution_code"),
        "status": result.get("status"),
        "audio_ready": bool(result.get("execution_code") == "PASSED" and result.get("output_path")),
    }
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.callback_total_timeout_s
    last_error = "nieznany błąd"
    attempts_made = 0

    timeout = httpx.Timeout(settings.callback_request_timeout_s)
    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        for attempt in range(1, settings.callback_max_attempts + 1):
            attempts_made = attempt
            remaining = deadline - loop.time()
            if remaining <= 0:
                last_error = "przekroczono całkowity timeout"
                break
            try:
                response = await asyncio.wait_for(
                    client.post(settings.callback_url, json=payload, headers=headers),
                    timeout=min(settings.callback_request_timeout_s, remaining),
                )
                if response.status_code < 400:
                    log.info("callback requestu %s dostarczony w próbie %s", request_id, attempt)
                    return True
                last_error = f"HTTP {response.status_code}"
                # Błędne uwierzytelnienie lub adres nie poprawią się po ponowieniu.
                if response.status_code < 500 and response.status_code not in {408, 429}:
                    break
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"

            if attempt >= settings.callback_max_attempts:
                break
            delay = settings.callback_retry_base_s * (2 ** (attempt - 1))
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            await sleep(min(delay, remaining))

    log.error(
        "callback requestu %s nie został dostarczony po %s próbach: %s",
        request_id,
        attempts_made,
        last_error,
    )
    return False
