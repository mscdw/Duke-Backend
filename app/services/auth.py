import httpx
import logging
import time
import hashlib
from app.core.config import get_settings

settings = get_settings()

AVIGILON_BASE_URL = settings.AVIGILON_BASE_URL
USERNAME = settings.AVIGILON_USERNAME
PASSWORD = settings.AVIGILON_PASSWORD
CLIENT_NAME = settings.AVIGILON_CLIENT_NAME
USER_NONCE = settings.AVIGILON_USER_NONCE
USER_KEY = settings.AVIGILON_USER_KEY

logger = logging.getLogger("avigilon-api")

def generate_auth_token():
    epoch = int(time.time())
    hash_input = f"{epoch}{USER_KEY}".encode('utf-8')
    hash_output = hashlib.sha256(hash_input).hexdigest()
    return f"{USER_NONCE}:{epoch}:{hash_output}"

async def authenticate():
    try:
        async with httpx.AsyncClient(verify=settings.AVIGILON_API_VERIFY_SSL, timeout=10) as client:
            response = await client.post(
                f"{AVIGILON_BASE_URL}/login",
                json={"username": USERNAME, "password": PASSWORD, "clientName": CLIENT_NAME, "authorizationToken": generate_auth_token()},
                headers={"content-type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Successfully authenticated with Avigilon API.")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise