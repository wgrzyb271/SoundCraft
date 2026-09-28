from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, HTTPException
from ..services import transfer_service, is_real_wav, convert_to_wav, save_upload, UploadType
from ..config import is_demo_mode
from uuid import uuid4
from pathlib import Path
import json

upload_router = APIRouter()

@upload_router.post("/upload")
async def upload(background_tasks: BackgroundTasks, prompt: str = Form(...), audio: UploadFile = File(...)):

    if not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty",
        )

    request_id = str(uuid4())
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True, exist_ok=True)

    try:
        demo = is_demo_mode()
        if not demo:
            transfer_service.create_request(request_id)
        original_filename = Path(audio.filename or "audio").name
        original_path = (request_dir / original_filename)
        await save_upload(audio, original_path)

        wav_path = (request_dir / "input" / "audio_folder" / "audio.wav") if demo else (request_dir / "audio.wav")
        wav_path.parent.mkdir(parents=True, exist_ok=True)

        if is_real_wav(original_path):
            original_path.rename(wav_path)
        else:
            convert_to_wav(original_path, wav_path)

        metadata = {
            "request_id": request_id,
            "prompt": prompt,
            "audio": "audio.wav"
        }

        metadata_path = (request_dir / "input" / "prompt_folder" / "metadata.json") if demo else (request_dir / "metadata.json")
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        if demo:
            from llm_agent.orchestrator.demo import process_demo_request

            background_tasks.add_task(process_demo_request, request_dir, prompt)
        else:
            transfer_service.transfer(wav_path, request_id, UploadType.AUDIO)
            transfer_service.transfer(metadata_path, request_id, UploadType.PROMPT)

        return {
            "status": "received",
            "request_id": request_id,
            "prompt": prompt,
            "filename": audio.filename
        }
    except Exception:
        if not is_demo_mode():
            try:
                transfer_service.delete_request(request_id)
            except Exception:
                pass
        raise
