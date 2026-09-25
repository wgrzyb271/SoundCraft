from fastapi import APIRouter,HTTPException
from ..services import transfer_service
from pathlib import Path
import json 
from fastapi.responses import FileResponse

result_router = APIRouter()

@result_router.get("/result/{request_id}")
def get_result(request_id:str):
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True, exist_ok=True)

    response_path = request_dir/"response.json"

    try:
        transfer_service.download_result(
            request_id,
            "response.json",
            response_path
        )
    except Exception:
        return {
            "status":"processing",
            "request_id":request_id
        }

    response = json.loads(
        response_path.read_text(encoding="utf-8")
    )
    return{
        "status":"completed",
        "request_id":request_id,
        "response":response
    }

@result_router.get("/result/{request_id}/audio")
def get_result_audio(request_id:str):
    request_dir = Path(f"/tmp/agent_requests/{request_id}")
    request_dir.mkdir(parents=True, exist_ok=True)

    audio_path = request_dir / "audio.wav"

    try:
        transfer_service.download_result(
            request_id,
            "audio.wav",
            audio_path
        )
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Audio is not ready"
        )

    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename="audio.wav"
    )

@result_router.delete("/result/{request_id}")
def delete_result(request_id: str):
    try:
        transfer_service.delete_request(
            request_id
        )

        return {
            "status": "deleted",
            "request_id": request_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not delete request: {e}",
        )