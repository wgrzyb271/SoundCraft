from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from ..services import transfer_service, is_real_wav, convert_to_wav, save_upload, UploadType
from uuid import uuid4
from pathlib import Path
import json 
from datetime import datetime, timezone, timedelta
from ..config import settings
upload_router = APIRouter()

@upload_router.post("/upload/audio/")
async def upload_audio(audio:UploadFile = File(...)):

    request_id = str(uuid4())
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True,exist_ok=True)

    try: 
        transfer_service.create_request(request_id)
        original_filename = Path(audio.filename or "audio").name
        original_path = (request_dir/original_filename)
        await save_upload(audio, original_path)

        wav_path = request_dir/"audio.wav"
        print(f"WAV_PATH: {wav_path}\n")
        if is_real_wav(original_path):
            original_path.rename(wav_path)
        else:
            convert_to_wav(original_path,wav_path)

        transfer_service.transfer(wav_path, request_id,UploadType.AUDIO)
    
        return {
            "status":"received",
            "request_id":request_id,
            "filename":audio.filename
        }
    except Exception:
        try:
            transfer_service.delete_request(request_id)
        except Exception:
            pass
        raise

@upload_router.post("/upload/{request_id}/prompt")
async def upload_prompt(request_id:str, prompt:str=Form(...)):
    if not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty",
        )
    try: 
        request_dir = Path(f"/tmp/agent_requests/{request_id}")
        request_dir.mkdir(parents=True,exist_ok=True)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.processing_ttl)
        metadata={
            "request_id":request_id,
            "prompt":prompt,
            "created_at":now.isoformat(),
            "expires_at":expires_at.isoformat(),
            "status":"processing"
        }

        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        prompt_path = request_dir/f"prompt_{timestamp}.json"
        prompt_path.write_text(json.dumps(metadata,indent=2),encoding="utf-8")

        print(f"METADATA_PATH: {prompt_path}\n")
        transfer_service.transfer(prompt_path,request_id, UploadType.PROMPT)

        return {
                "status":"received",
                "request_id":request_id,
                "prompt":prompt
            }
    except Exception:
        try:
            transfer_service.delete_request(request_id)
        except Exception:
            pass
        raise
