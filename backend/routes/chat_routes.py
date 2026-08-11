from fastapi import APIRouter, Depends
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationListItem,
    ConversationDetailResponse,
    RenameConversationRequest,
)
from services.chat_service import ChatService
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/{repository_id}/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    repository_id: str,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.list_conversations(repository_id, str(current_user._id))


@router.post("/{repository_id}/conversations", response_model=ConversationDetailResponse)
async def create_conversation(
    repository_id: str,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.create_conversation(repository_id, str(current_user._id))


@router.get("/{repository_id}/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    repository_id: str,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.get_conversation(repository_id, conversation_id, str(current_user._id))


@router.patch("/{repository_id}/conversations/{conversation_id}", response_model=ConversationListItem)
async def rename_conversation(
    repository_id: str,
    conversation_id: str,
    data: RenameConversationRequest,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.rename_conversation(
        repository_id, conversation_id, str(current_user._id), data.title
    )


@router.delete("/{repository_id}/conversations/{conversation_id}")
async def delete_conversation(
    repository_id: str,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.delete_conversation(repository_id, conversation_id, str(current_user._id))


@router.post("/message", response_model=ChatResponse)
async def send_message(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    service = ChatService()
    return service.chat(
        repository_id=data.repository_id,
        conversation_id=data.conversation_id,
        message=data.message,
        user_id=str(current_user._id),
    )
