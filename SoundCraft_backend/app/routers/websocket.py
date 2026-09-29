from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router= APIRouter()

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str,WebSocket]={}

    async def connect(self, request_id:str,websocket:WebSocket):
        await websocket.accept()
        self.connections[request_id]=websocket

    def disconnect(self, request_id:str):
        self.connections.pop(request_id,None)

    async def notify(self, request_id:str, message:dict):
        websocket = self.connections.get(request_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(request_id)

manager = ConnectionManager()

@ws_router.websocket("/ws/{request_id}")
async def websocket_endpoint(websocket:WebSocket, request_id:str):
    await manager.connect(request_id,websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(request_id)

#temp endpoint for testing Frontend-Backend connection
@ws_router.post("/ws-test/{request_id}/complete")
async def test_complete(request_id: str):
    await manager.notify(
        request_id,
        {
            "type": "completed",
            "request_id": request_id,
        },
    )

    return {
        "status": "sent",
        "request_id": request_id,
    }