from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router= APIRouter()

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str,WebSocket]={}

    async def connect(self, request_id:str,websocket:WebSocket):
        print(f"WS CONNECT: {request_id}")
        print(f"WS BEFORE: {len(self.connections)} connections")
        await websocket.accept()
        self.connections[request_id]=websocket
        print(f"WS AFTER: {len(self.connections)} connections")

    def disconnect(self, request_id:str):
        print(f"WS DISCONNECT: {request_id}")
        self.connections.pop(request_id,None)
        print(f"WS AFTER DISCONNECT: {len(self.connections)} connections")

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