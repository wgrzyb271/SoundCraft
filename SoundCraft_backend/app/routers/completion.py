from __future__ import annotations

import hmac
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..completion import completion_registry
from ..config import settings

completion_router = APIRouter()


class CompletionNotice(BaseModel):
    request_id: str
    execution_code: Literal["PASSED", "FAILED"] | None = None
    status: str | None = None
    audio_ready: bool = False


@completion_router.post("/internal/ml/completed", include_in_schema=False)
async def ml_completed(
    notice: CompletionNotice,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    try:
        UUID(notice.request_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid request_id") from exc

    if not settings.callback_token:
        raise HTTPException(status_code=503, detail="Completion callback is not configured")
    expected = f"Bearer {settings.callback_token}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid callback token")

    await completion_registry.mark_completed(notice.request_id, notice.model_dump())
    return {"status": "accepted", "request_id": notice.request_id}


@completion_router.websocket("/ws/result/{request_id}")
async def result_websocket(websocket: WebSocket, request_id: str) -> None:
    try:
        UUID(request_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid request_id")
        return

    await websocket.accept()
    try:
        payload: dict[str, Any] | None = await completion_registry.wait(
            request_id, settings.completion_wait_timeout
        )
        if payload is None:
            await websocket.send_json({"status": "timeout", "request_id": request_id})
        else:
            await websocket.send_json({**payload, "status": "completed"})
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
