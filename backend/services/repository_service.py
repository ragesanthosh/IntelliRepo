from fastapi import HTTPException, status
from models.user import Repository
from repositories.repository_repository import RepositoryRepository
from utils.github import parse_github_url
from rag.ingestor import (
    ingest_repository,
    reindex_repository,
    get_collection_name,
    RepositoryCloneError,
    EmptyRepositoryError,
    IngestionError,
    EmbeddingError,
    VectorStoreError,
)
from rag.embedder import collection_exists, is_collection_compatible
from ai.gemini import generate_repository_analysis, GeminiAPIError


ANALYSIS_STEPS = [
    "validating",
    "cloning",
    "reading",
    "embedding",
    "understanding",
    "generating",
    "finishing",
]

_progress_store: dict[str, dict] = {}


class RepositoryService:
    def __init__(self):
        self.repo_repo = RepositoryRepository()

    def get_progress(self, analysis_id: str) -> dict:
        return _progress_store.get(analysis_id, {"steps": [], "status": "unknown"})

    def _update_progress(self, analysis_id: str, step: str, step_status: str, overall: str = "in_progress"):
        if analysis_id not in _progress_store:
            _progress_store[analysis_id] = {"steps": [], "status": overall}

        steps = _progress_store[analysis_id]["steps"]
        existing = next((s for s in steps if s["step"] == step), None)
        if existing:
            existing["status"] = step_status
        else:
            steps.append({"step": step, "status": step_status})

        _progress_store[analysis_id]["status"] = overall

    def analyze(self, url: str, user_id: str) -> dict:
        parsed = parse_github_url(url)
        if not parsed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub repository URL. Use format: https://github.com/owner/repo",
            )

        owner, repo_name, normalized_url = parsed
        analysis_id = f"{user_id}_{owner}_{repo_name}"

        existing = self.repo_repo.find_by_url_and_user(normalized_url, user_id)
        collection_name = get_collection_name(owner, repo_name)

        # Reuse cached analysis only when summary + compatible vector index exist
        if (
            existing
            and existing.summary
            and collection_exists(collection_name)
            and is_collection_compatible(collection_name)
        ):
            return {
                "id": str(existing._id),
                "repository_name": existing.repository_name,
                "owner": existing.owner,
                "repository_url": existing.repository_url,
                "status": "completed",
                "message": "Repository already analyzed. Loading cached results.",
                "cached": True,
            }

        try:
            self._update_progress(analysis_id, "validating", "completed")
            self._update_progress(analysis_id, "cloning", "in_progress")

            # Re-index when format is incompatible; otherwise ingest (may reuse cache)
            incompatible = (
                collection_exists(collection_name)
                and not is_collection_compatible(collection_name)
            )
            force_reindex = incompatible

            collection_name, files, folder_structure = ingest_repository(
                normalized_url,
                owner,
                repo_name,
                force_reindex=force_reindex,
            )

            self._update_progress(analysis_id, "cloning", "completed")
            self._update_progress(analysis_id, "reading", "completed")
            self._update_progress(analysis_id, "embedding", "completed")
            self._update_progress(analysis_id, "understanding", "in_progress")

            # Preserve existing summary when only upgrading the vector index
            if existing and existing.summary and incompatible:
                summary = existing.summary
            else:
                summary = generate_repository_analysis(
                    owner, repo_name, normalized_url, files, folder_structure
                )

            self._update_progress(analysis_id, "understanding", "completed")
            self._update_progress(analysis_id, "generating", "completed")
            self._update_progress(analysis_id, "finishing", "in_progress")

            if existing:
                self.repo_repo.update_summary(str(existing._id), summary, collection_name)
                repo = existing
                repo.summary = summary
                repo.chroma_collection = collection_name
            else:
                repo = Repository(
                    user_id=user_id,
                    repository_name=repo_name,
                    repository_url=normalized_url,
                    owner=owner,
                    summary=summary,
                    chroma_collection=collection_name,
                )
                repo = self.repo_repo.create(repo)

            self._update_progress(analysis_id, "finishing", "completed", "completed")

            return {
                "id": str(repo._id),
                "repository_name": repo.repository_name,
                "owner": repo.owner,
                "repository_url": repo.repository_url,
                "status": "completed",
                "message": "Analysis completed successfully.",
                "cached": False,
            }

        except RepositoryCloneError as e:
            self._update_progress(analysis_id, "cloning", "error", "error")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except EmptyRepositoryError as e:
            self._update_progress(analysis_id, "reading", "error", "error")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except IngestionError as e:
            self._update_progress(analysis_id, "reading", "error", "error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Source ingestion failed. Please try again.",
            ) from e
        except EmbeddingError:
            self._update_progress(analysis_id, "embedding", "error", "error")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding failed. Please try again shortly.",
            )
        except VectorStoreError:
            self._update_progress(analysis_id, "embedding", "error", "error")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector store failed. Please try again shortly.",
            )
        except GeminiAPIError as e:
            self._update_progress(analysis_id, "understanding", "error", "error")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "resourceexhausted" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gemini API quota exceeded for this model. Try a different GEMINI_MODEL in .env (e.g. gemini-2.5-flash) or wait and retry.",
                )
            if "api key" in error_msg.lower() or "invalid" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Invalid Gemini API key. Get a key from https://aistudio.google.com/apikey",
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI analysis service temporarily unavailable. Please try again later.",
            )
        except Exception as e:
            self._update_progress(analysis_id, "understanding", "error", "error")
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "resourceexhausted" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gemini API quota exceeded for this model. Try a different GEMINI_MODEL in .env (e.g. gemini-2.5-flash) or wait and retry.",
                )
            if "api key" in error_msg.lower() or "invalid" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Invalid Gemini API key. Get a key from https://aistudio.google.com/apikey",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Analysis failed. Please try again.",
            )

    def reindex(self, repo_id: str, user_id: str) -> dict:
        """
        Safely re-index vectors with the latest chunking/metadata format.
        Preserves MongoDB repository metadata and summary.
        """
        repo = self.repo_repo.find_by_id(repo_id)
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        if repo.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        try:
            collection_name, _files, _structure = reindex_repository(
                repo.repository_url,
                repo.owner,
                repo.repository_name,
            )
            self.repo_repo.update_summary(str(repo._id), repo.summary or {}, collection_name)
            return {
                "id": str(repo._id),
                "repository_name": repo.repository_name,
                "owner": repo.owner,
                "repository_url": repo.repository_url,
                "status": "completed",
                "message": "Repository vector index rebuilt successfully.",
                "cached": False,
            }
        except RepositoryCloneError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except EmptyRepositoryError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except EmbeddingError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Embedding failed during re-index. Please try again.",
            )
        except VectorStoreError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector store failed during re-index. Please try again.",
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Re-index failed. Please try again.",
            )

    def list_repositories(self, user_id: str) -> list[dict]:
        repos = self.repo_repo.find_by_user(user_id)
        return [r.to_list_item() for r in repos]

    def get_repository(self, repo_id: str, user_id: str) -> dict:
        repo = self.repo_repo.find_by_id(repo_id)
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        if repo.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return repo.to_response(include_summary=True)
