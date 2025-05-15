from fastapi import FastAPI
from app.services.scheduler import start_scheduler

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    start_scheduler()
