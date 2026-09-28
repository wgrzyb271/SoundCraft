from fastapi import FastAPI
from .endpoints import upload_router, result_router
from fastapi.middleware.cors import CORSMiddleware
import os
app=FastAPI()

frontend_origins = [
    origin.strip()
    for origin in os.environ.get(
        "SOUNDCRAFT_FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(upload_router)
app.include_router(result_router)
#run:  uvicorn app.main:app --reload
