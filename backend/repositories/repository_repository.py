from bson import ObjectId
from database.connection import get_database
from models.user import Repository


class RepositoryRepository:
    def __init__(self):
        self.collection = get_database()["repositories"]

    def create(self, repo: Repository) -> Repository:
        result = self.collection.insert_one(repo.to_dict())
        repo._id = result.inserted_id
        return repo

    def find_by_id(self, repo_id: str) -> Repository | None:
        try:
            data = self.collection.find_one({"_id": ObjectId(repo_id)})
        except Exception:
            return None
        return Repository.from_dict(data) if data else None

    def find_by_user(self, user_id: str) -> list[Repository]:
        cursor = self.collection.find({"userId": user_id}).sort("createdAt", -1)
        return [Repository.from_dict(doc) for doc in cursor]

    def find_by_url_and_user(self, url: str, user_id: str) -> Repository | None:
        data = self.collection.find_one({"repositoryUrl": url, "userId": user_id})
        return Repository.from_dict(data) if data else None

    def update_summary(self, repo_id: str, summary: dict, chroma_collection: str) -> bool:
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(repo_id)},
                {"$set": {"summary": summary, "chromaCollection": chroma_collection}},
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, repo_id: str) -> bool:
        try:
            result = self.collection.delete_one({"_id": ObjectId(repo_id)})
            return result.deleted_count > 0
        except Exception:
            return False
