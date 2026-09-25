from fastapi import APIRouter,HTTPException
from ..services import transfer_service, ResultType
from pathlib import Path
import json 
from fastapi.responses import FileResponse
from datetime import datetime,timezone

result_router = APIRouter()

def get_request_dir(request_id:str)->Path:
    return Path(f"/tmp/agent_requests/{request_id}")

def is_expired(request_id:str)->bool:
    request_dir = get_request_dir(request_id)
    metadata_files = list(request_dir.glob("prompt_*.json"))

    if not metadata_files:
        return False
    
    latest_metadata = max(metadata_files,key=lambda path: path.stat().st_mtime)
    metadata = json.loads(latest_metadata.read_text(encoding="utf-8"))
    expires_at = datetime.fromisoformat(metadata["expires_at"])
    return datetime.now(timezone.utc) >= expires_at

def get_latest_result(request_id:str, result_type:ResultType):
    files = transfer_service.list_result_files(request_id,result_type)
    if not files:
        return None
    latest_file = max(files, key=lambda file:file.st_mtime)
    return latest_file.filename
        
@result_router.get("/result/{request_id}/agent_response")
def get_result(request_id:str):
    if is_expired(request_id):
        return {
            "status":"expired",
            "request_id":request_id
        }
    try:
        latest_filename = get_latest_result(request_id,ResultType.AGENT_RESPONSE)

        if latest_filename is None:
            return{
                "status": "processing",
                "request_id": request_id
            }
        request_dir = get_request_dir(request_id)
        response_path = (request_dir / "latest_response.json")
        transfer_service.download_result(request_id, latest_filename, response_path, ResultType.AGENT_RESPONSE )

    except Exception as e:
        print (f"Could not get agent response: {e}") 
        return{
            "status": "processing",
            "request_id": request_id
            }

    try:
        response = json.loads(response_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Could not parse response: {e}")
        raise HTTPException(status_code=500,detail="Invalid agent response")
    return{
        "status": "completed",
        "request_id": request_id,
        "filename": latest_filename,
        "response": response
    }

@result_router.get("/result/{request_id}/audio")
def get_result_audio(request_id:str):
    if is_expired(request_id):
        raise HTTPException(status_code=410, detail="Request has expired")

    try:
        latest_filename = get_latest_result(request_id, ResultType.AUDIO)

        if latest_filename is None:
            raise HTTPException(status_code=404, detail="Audio is not ready")

        request_dir = get_request_dir(request_id)
        audio_path = request_dir/latest_filename
        
        print(f"LATEST AUDIO: {latest_filename}")
        print(f"LOCAL AUDIO PATH: {audio_path}")

        transfer_service.download_result(
            request_id,
            latest_filename,
            audio_path,
            ResultType.AUDIO
        )
    except HTTPException:
        raise

    except Exception as e:
        print (f"Could not get audio:{e}")
        raise HTTPException(status_code=404, detail="Audio is not ready")

    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename="audio.wav"
    )

@result_router.delete("/result/{request_id}")
def delete_result(request_id: str):
    try:
        transfer_service.delete_request(request_id)

        return {
            "status": "deleted",
            "request_id": request_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Could not delete request: {e}")