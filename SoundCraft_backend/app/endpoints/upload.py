from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from ..services import transfer_service, is_real_wav, convert_to_wav, save_upload
from uuid import uuid4
from pathlib import Path
import json 

upload_router = APIRouter()

@upload_router.post("/upload")
async def upload(prompt:str=Form(...),audio:UploadFile = File(...)):

    if not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty",
        )

    request_id = str(uuid4())
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True,exist_ok=True)

    try: 
        transfer_service.create_request(request_id)
        original_filename = Path(audio.filename or "audio").name
        original_path = (request_dir/original_filename)
        await save_upload(audio, original_path)

        wav_path = request_dir/"audio.wav"

        if is_real_wav(original_path):
            original_path.rename(wav_path)
        else:
            convert_to_wav(original_path,wav_path)

            metadata = {
                "request_id":request_id,
                "prompt":prompt,
                "audio":"audio.wav"
            }

        metadata_path = request_dir/"metadata.json"
        metadata_path.write_text(json.dumps(metadata,indent=2),encoding="utf-8")

        transfer_service.transfer(wav_path, request_id)
        transfer_service.transfer(metadata_path, request_id)
    
        return {
            "status":"received",
            "request_id":request_id,
            "prompt":prompt,
            "filename":audio.filename
        }
    except Exception:
        try:
            transfer_service.delete_request(request_id)
        except Exception:
            pass
        raise