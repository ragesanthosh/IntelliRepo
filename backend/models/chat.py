from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_title(message: str, max_len: int = 48) -> str:
    title = message.strip().replace("\n", " ")
    if len(title) <= max_len:
        return title or "New Chat"
    return title[: max_len - 3].rstrip() + "..."


class ChatMessage:
    def __init__(self, role: str, content: str, created_at=None):
        self.role = role
        self.content = content
        self.created_at = created_at or utc_now()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            created_at=data.get("createdAt"),
        )


class Conversation:
    def __init__(
        self,
        user_id: str,
        repository_id: str,
        title: str = "New Chat",
        messages: list[ChatMessage] | None = None,
        _id=None,
        created_at=None,
        updated_at=None,
    ):
        self._id = _id
        self.user_id = user_id
        self.repository_id = repository_id
        self.title = title
        self.messages = messages or []
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or utc_now()

    def to_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "repositoryId": self.repository_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            _id=data.get("_id"),
            user_id=data["userId"],
            repository_id=data["repositoryId"],
            title=data.get("title", "New Chat"),
            messages=messages,
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def to_list_item(self) -> dict:
        return {
            "id": str(self._id),
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def to_detail(self) -> dict:
        return {
            "id": str(self._id),
            "repository_id": self.repository_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in self.messages
            ],
        }
