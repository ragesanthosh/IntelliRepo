from bson import ObjectId
from database.connection import get_database
from models.user import User


class UserRepository:
    def __init__(self):
        self.collection = get_database()["users"]

    def create(self, user: User) -> User:
        result = self.collection.insert_one(user.to_dict())
        user._id = result.inserted_id
        return user

    def find_by_email(self, email: str) -> User | None:
        data = self.collection.find_one({"email": email.lower()})
        return User.from_dict(data) if data else None

    def find_by_id(self, user_id: str) -> User | None:
        try:
            data = self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        return User.from_dict(data) if data else None

    def email_exists(self, email: str) -> bool:
        return self.collection.count_documents({"email": email.lower()}) > 0
