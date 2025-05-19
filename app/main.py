import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.auth import authenticate
# from .events import router as events_router
# from .webhooks import router as webhook_router
# from .duke_proxy import router as duke_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("avigilon-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up and authenticating with Avigilon API...")
    await authenticate()
    logger.info("Authentication complete.")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="Avigilon Integration API",
    description="FastAPI application for interacting with Avigilon REST APIs and receiving event webhooks.",
    version="1.0.0",
    contact={
        "name": "Avigilon Dev Team",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

@app.get("/")
def index():
    return "Welcome to Duke proxy API"

# app.include_router(events_router, tags=["Events"])
# app.include_router(webhook_router, tags=["Webhooks"])
# app.include_router(duke_router, tags=["Duke Proxy"])