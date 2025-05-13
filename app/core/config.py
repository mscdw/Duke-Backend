from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Avigilon Web Endpoints"
    database_url: str = "postgresql://user:password@localhost/dbname"

    class Config:
        env_file = ".env"
