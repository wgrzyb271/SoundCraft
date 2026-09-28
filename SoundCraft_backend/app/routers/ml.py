from fastapi import APIRouter
from pydantic import BaseModel
from .websocket import manager

ml_router = APIRouter()

class MLCompletedRequest(BaseModel):
    request_id = str

@ml_router.post("/internal/ml/completed")
async def ml_completed (data:MLCompletedRequest):
    await manager.notify(
        data.request_id,
        {
            "type":"completed",
            "request_id":data.request_id,
        },
    )
    return {
        "status":"ok",
        "request_id":data.request_id
    }