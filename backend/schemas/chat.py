from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    repository_id: str
    conversation_id: str
    message: str = Field(..., min_length=1, max_length=2000)


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str
    sources: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    title: str | None = None


class ConversationListItem(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetailResponse(BaseModel):
    id: str
    repository_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageResponse]
