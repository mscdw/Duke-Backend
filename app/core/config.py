from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AVIGILON_BASE: str = ""
    AVIGILON_USERNAME: str = ""
    AVIGILON_PASSWORD: str = ""
    AVIGILON_CLIENT_NAME: str = ""
    AVIGILON_USER_NONCE: str = ""
    AVIGILON_USER_KEY: str = ""
    AVIGILON_API_VERIFY_SSL: bool = False
    SESSION_TOKEN: str = ""
    CENTRAL_BASE: str = ""
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
