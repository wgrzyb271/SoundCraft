from fastapi import FastAPI
from .routers import upload_router, result_router, ws_router, ml_router
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""]
)
app.include_router(upload_router)
app.include_router(result_router)
app.include_router(ws_router)
app.include_router(ml_router)
#run:  uvicorn app.main:app --reload