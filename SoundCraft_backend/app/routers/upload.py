from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..completion import completion_registry
from ..config import is_demo_mode, settings
from ..services import UploadType, convert_to_wav, is_real_wav, save_upload, transfer_service

upload_router = APIRouter()


async def _process_demo_and_notify(request_dir: Path, prompt: str) -> None:
    from llm_agent.orchestrator.demo import process_demo_request

    payload = await process_demo_request(request_dir, prompt)
    await completion_registry.mark_completed(
        request_dir.name,
        {
            "request_id": request_dir.name,
            "execution_code": payload.get("execution_code"),
            "status": payload.get("status"),
            "audio_ready": bool(
                payload.get("execution_code") == "PASSED" and payload.get("output_path")
            ),
        },
    )


@upload_router.post("/upload/audio/")
async def upload_audio(audio: UploadFile = File(...)):
    request_id = str(uuid4())
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True, exist_ok=True)

    try:
        demo = is_demo_mode()
        if not demo:
            transfer_service.create_request(request_id)

        original_filename = Path(audio.filename or "audio").name
        original_path = request_dir / original_filename
        await save_upload(audio, original_path)

        wav_path = (
            request_dir / "input" / "audio_folder" / "audio.wav"
            if demo
            else request_dir / "audio.wav"
        )
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        if is_real_wav(original_path):
            original_path.rename(wav_path)
        else:
            convert_to_wav(original_path, wav_path)

        if not demo:
            transfer_service.transfer(wav_path, request_id, UploadType.AUDIO)

        return {
            "status": "received",
            "request_id": request_id,
            "filename": audio.filename,
        }
    except Exception:
        if not is_demo_mode():
            try:
                transfer_service.delete_request(request_id)
            except Exception:
                pass
        raise


@upload_router.post("/upload/{request_id}/prompt")
async def upload_prompt(
    request_id: str,
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
):
    try:
        UUID(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid request_id") from exc
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    if not request_dir.is_dir():
        raise HTTPException(status_code=404, detail="Request does not exist")

    try:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.processing_ttl)
        metadata = {
            "request_id": request_id,
            "prompt": prompt,
            "audio": "audio.wav",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "processing",
        }

        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        demo = is_demo_mode()
        prompt_path = (
            request_dir / "input" / "prompt_folder" / f"prompt_{timestamp}.json"
            if demo
            else request_dir / f"prompt_{timestamp}.json"
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        if demo:
            background_tasks.add_task(_process_demo_and_notify, request_dir, prompt)
        else:
            transfer_service.transfer(prompt_path, request_id, UploadType.PROMPT)

        return {"status": "received", "request_id": request_id, "prompt": prompt}
    except Exception:
        if not is_demo_mode():
            try:
                transfer_service.delete_request(request_id)
            except Exception:
                pass
        raise
