import logging
from fastapi import APIRouter, Request, Response, Query
from typing import Optional
import httpx
from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger("avigilon-endpoints")
settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
base_url = settings.AVIGILON_BASE_URL