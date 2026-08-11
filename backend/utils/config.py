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
    chunk_size: int = 1200
    chunk_overlap: int = 150
    temp_clone_dir: str = "./temp_repos"

    # RAG retrieval tuning
    rag_candidate_k: int = 12
    rag_final_k: int = 5
    rag_keyword_k: int = 10
    rag_min_relevance: float = 0.22
    rag_debug: bool = False
    rag_chunk_format_version: str = "2"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
