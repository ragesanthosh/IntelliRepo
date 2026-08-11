from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from database.connection import get_database
from models.chat import Conversation, generate_title


class ConversationRepository:
    def __init__(self):
        self.collection = get_database()["conversations"]

    def _query(self, user_id: str, repository_id: str, conversation_id: str) -> dict:
        return {
            "_id": ObjectId(conversation_id),
            "userId": user_id,
            "repositoryId": repository_id,
        }

    def list_by_repo(self, user_id: str, repository_id: str) -> list[Conversation]:
        cursor = self.collection.find({
            "userId": user_id,
            "repositoryId": repository_id,
        }).sort("updatedAt", -1)
        return [Conversation.from_dict(doc) for doc in cursor]

    def find_by_id(self, user_id: str, repository_id: str, conversation_id: str) -> Conversation | None:
        try:
            data = self.collection.find_one(self._query(user_id, repository_id, conversation_id))
        except Exception:
            return None
        return Conversation.from_dict(data) if data else None

    def create(self, user_id: str, repository_id: str, title: str = "New Chat") -> Conversation:
        now = datetime.now(timezone.utc)
        conversation = Conversation(
            user_id=user_id,
            repository_id=repository_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        result = self.collection.insert_one(conversation.to_dict())
        conversation._id = result.inserted_id
        return conversation

    def append_messages(
        self,
        user_id: str,
        repository_id: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        update_title: bool = False,
    ) -> Conversation | None:
        now = datetime.now(timezone.utc)
        new_messages = [
            {"role": "user", "content": user_message, "createdAt": now},
            {"role": "assistant", "content": assistant_message, "createdAt": now},
        ]

        update_fields: dict = {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"updatedAt": now},
        }
        if update_title:
            update_fields["$set"]["title"] = generate_title(user_message)

        try:
            result = self.collection.find_one_and_update(
                self._query(user_id, repository_id, conversation_id),
                update_fields,
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            return None
        return Conversation.from_dict(result) if result else None

    def rename(self, user_id: str, repository_id: str, conversation_id: str, title: str) -> Conversation | None:
        title = title.strip()
        if not title:
            return None
        try:
            result = self.collection.find_one_and_update(
                self._query(user_id, repository_id, conversation_id),
                {"$set": {"title": title[:100], "updatedAt": datetime.now(timezone.utc)}},
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            return None
        return Conversation.from_dict(result) if result else None

    def delete(self, user_id: str, repository_id: str, conversation_id: str) -> bool:
        try:
            result = self.collection.delete_one(self._query(user_id, repository_id, conversation_id))
            return result.deleted_count > 0
        except Exception:
            return False

    def delete_by_repository(self, repository_id: str) -> None:
        self.collection.delete_many({"repositoryId": repository_id})
