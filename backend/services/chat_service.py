from fastapi import HTTPException, status
from repositories.repository_repository import RepositoryRepository
from repositories.chat_repository import ConversationRepository
from rag.retriever import retrieve_relevant_chunks
from ai.gemini import generate_chat_response


class ChatService:
    def __init__(self):
        self.repo_repo = RepositoryRepository()
        self.conversation_repo = ConversationRepository()

    def _verify_repo_access(self, repository_id: str, user_id: str):
        repo = self.repo_repo.find_by_id(repository_id)
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        if repo.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return repo

    def _get_conversation(self, repository_id: str, conversation_id: str, user_id: str):
        conversation = self.conversation_repo.find_by_id(user_id, repository_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    def list_conversations(self, repository_id: str, user_id: str) -> list[dict]:
        self._verify_repo_access(repository_id, user_id)
        conversations = self.conversation_repo.list_by_repo(user_id, repository_id)
        return [c.to_list_item() for c in conversations]

    def create_conversation(self, repository_id: str, user_id: str) -> dict:
        self._verify_repo_access(repository_id, user_id)
        conversation = self.conversation_repo.create(user_id, repository_id)
        return conversation.to_detail()

    def get_conversation(self, repository_id: str, conversation_id: str, user_id: str) -> dict:
        self._verify_repo_access(repository_id, user_id)
        conversation = self._get_conversation(repository_id, conversation_id, user_id)
        return conversation.to_detail()

    def rename_conversation(
        self, repository_id: str, conversation_id: str, user_id: str, title: str
    ) -> dict:
        self._verify_repo_access(repository_id, user_id)
        conversation = self.conversation_repo.rename(user_id, repository_id, conversation_id, title)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation.to_list_item()

    def delete_conversation(self, repository_id: str, conversation_id: str, user_id: str) -> dict:
        self._verify_repo_access(repository_id, user_id)
        deleted = self.conversation_repo.delete(user_id, repository_id, conversation_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return {"message": "Conversation deleted"}

    def chat(
        self,
        repository_id: str,
        conversation_id: str,
        message: str,
        user_id: str,
    ) -> dict:
        repo = self._verify_repo_access(repository_id, user_id)
        conversation = self._get_conversation(repository_id, conversation_id, user_id)

        if not repo.chroma_collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository has not been analyzed yet",
            )

        context_history = [{"role": m.role, "content": m.content} for m in conversation.messages]

        try:
            chunks = retrieve_relevant_chunks(repo.chroma_collection, message, top_k=5)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to search repository. Please try again.",
            )

        sources = list({c["source"] for c in chunks})

        try:
            answer = generate_chat_response(
                question=message,
                summary=repo.summary or {},
                context_chunks=chunks,
                history=context_history,
            )
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gemini API quota exceeded. Please try again later.",
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service temporarily unavailable. Please try again later.",
            )

        is_first_message = len(conversation.messages) == 0
        updated = self.conversation_repo.append_messages(
            user_id,
            repository_id,
            conversation_id,
            message,
            answer,
            update_title=is_first_message and conversation.title == "New Chat",
        )

        new_title = updated.title if updated else conversation.title

        return {"answer": answer, "sources": sources, "title": new_title if is_first_message else None}
