from pymongo import MongoClient
from pymongo.database import Database
from utils.config import get_settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_database() -> Database:
    settings = get_settings()
    return get_client()[settings.database_name]


def close_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None
