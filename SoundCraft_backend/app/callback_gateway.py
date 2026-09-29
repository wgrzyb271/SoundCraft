"""Minimalny publiczny ingress callbacku; nie wystawia uploadu ani wyników."""
from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


class CompletionNotice(BaseModel):
    request_id: str
    execution_code: str | None = None
    status: str | None = None
    audio_ready: bool = False


app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/ml/completed")
async def completed(
    notice: CompletionNotice,
    authorization: str | None = Header(default=None),
) -> dict:
    backend_url = os.environ.get("SOUNDCRAFT_INTERNAL_BACKEND_URL", "http://127.0.0.1:8000")
    headers = {"Authorization": authorization} if authorization else {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{backend_url.rstrip('/')}/internal/ml/completed",
                json=notice.model_dump(),
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Local backend is unavailable") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text[:500])
    return response.json()
