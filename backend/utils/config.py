from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    gemini_api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "IntelliRepo"
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_db_path: str = "./chroma"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    chunk_size: int = 1000
    chunk_overlap: int = 200
    temp_clone_dir: str = "./temp_repos"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
