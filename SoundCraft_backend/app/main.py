from fastapi import FastAPI
from .endpoints import upload_router, result_router

app=FastAPI()
app.include_router(upload_router)
app.include_router(result_router)
#run:  uvicorn app.main:app --reload