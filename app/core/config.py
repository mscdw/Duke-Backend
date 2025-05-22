from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AVIGILON_BASE_URL: str = ""
    AVIGILON_USERNAME: str = ""
    AVIGILON_PASSWORD: str = ""
    AVIGILON_CLIENT_NAME: str = ""
    AVIGILON_USER_NONCE: str = ""
    AVIGILON_USER_KEY: str = ""
    AVIGILON_API_VERIFY_SSL: bool = False
    LOG_LEVEL: str = "INFO"
    SESSION_TOKEN: str = "AXUAiv8KEDwecCpYnExqpbLKs4o-P0QSFgoUcoahlIJ7oc7ICRPhqi88n-fN5iIaEPS_gZgRUk4_iIWJpKZdJSEiEJ3v7ciUrk-1vErULZEKhfAqBmNoYXJhbjIdGhD15XlQda5BXYa0iielLzcHKglkZXZlbG9wZXI"
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
