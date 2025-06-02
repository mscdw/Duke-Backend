import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.auth import authenticate
from app.api.endpoints import router
from app.api.server_events import router as server_events_router
from app.api.appearance_events import router as appearance_events_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("avigilon-base")

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

app.include_router(router)
app.include_router(server_events_router)
app.include_router(appearance_events_router)