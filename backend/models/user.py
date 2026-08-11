from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User:
    def __init__(self, name: str, email: str, password: str, _id=None, created_at=None):
        self._id = _id
        self.name = name
        self.email = email
        self.password = password
        self.created_at = created_at or utc_now()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email.lower(),
            "password": self.password,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            _id=data.get("_id"),
            name=data["name"],
            email=data["email"],
            password=data["password"],
            created_at=data.get("createdAt"),
        )

    def to_response(self) -> dict:
        return {
            "id": str(self._id),
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class Repository:
    def __init__(
        self,
        user_id: str,
        repository_name: str,
        repository_url: str,
        owner: str,
        summary: Optional[dict] = None,
        chroma_collection: Optional[str] = None,
        _id=None,
        created_at=None,
    ):
        self._id = _id
        self.user_id = user_id
        self.repository_name = repository_name
        self.repository_url = repository_url
        self.owner = owner
        self.summary = summary
        self.chroma_collection = chroma_collection
        self.created_at = created_at or utc_now()

    def to_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "repositoryName": self.repository_name,
            "repositoryUrl": self.repository_url,
            "owner": self.owner,
            "summary": self.summary,
            "chromaCollection": self.chroma_collection,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Repository":
        return cls(
            _id=data.get("_id"),
            user_id=data["userId"],
            repository_name=data["repositoryName"],
            repository_url=data["repositoryUrl"],
            owner=data["owner"],
            summary=data.get("summary"),
            chroma_collection=data.get("chromaCollection"),
            created_at=data.get("createdAt"),
        )

    def to_response(self, include_summary: bool = True) -> dict:
        result = {
            "id": str(self._id),
            "repository_name": self.repository_name,
            "repository_url": self.repository_url,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
        if include_summary:
            result["summary"] = self.summary
        return result

    def to_list_item(self) -> dict:
        return {
            "id": str(self._id),
            "repository_name": self.repository_name,
            "owner": self.owner,
            "repository_url": self.repository_url,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
