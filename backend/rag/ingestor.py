import os
import shutil
from git import Repo
from git.exc import GitCommandError
from utils.config import get_settings
from utils.file_reader import read_repository_files, get_folder_structure
from rag.chunker import chunk_documents, CHUNK_FORMAT_VERSION
from rag.embedder import (
    store_embeddings,
    collection_exists,
    is_collection_compatible,
    delete_collection,
)
from rag.debug import log_rag_event


class RepositoryCloneError(Exception):
    pass


class EmptyRepositoryError(Exception):
    pass


class IngestionError(Exception):
    pass


class EmbeddingError(Exception):
    pass


class VectorStoreError(Exception):
    pass


def get_collection_name(owner: str, repo_name: str) -> str:
    raw = f"{owner}_{repo_name}".lower()
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in raw)
    return f"repo_{safe}"


def clone_repository(url: str, owner: str, repo_name: str) -> str:
    settings = get_settings()
    os.makedirs(settings.temp_clone_dir, exist_ok=True)

    clone_path = os.path.join(settings.temp_clone_dir, f"{owner}_{repo_name}")

    if os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)

    try:
        Repo.clone_from(url, clone_path, depth=1)
    except GitCommandError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg or "404" in error_msg:
            raise RepositoryCloneError("Repository not found. Please check the URL.")
        if "authentication" in error_msg or "403" in error_msg or "permission" in error_msg:
            raise RepositoryCloneError(
                "This appears to be a private repository. Only public repositories are supported."
            )
        raise RepositoryCloneError("Failed to clone repository. Please verify the URL and try again.")

    return clone_path


def _index_files(collection_name: str, files: list[dict], repository: str) -> None:
    try:
        chunks = chunk_documents(files, repository=repository)
    except Exception as e:
        raise IngestionError("Failed to process source files for indexing.") from e

    if not chunks:
        raise EmptyRepositoryError("No indexable source chunks found in this repository.")

    log_rag_event("Indexing", {
        "collection": collection_name,
        "files": len(files),
        "chunks": len(chunks),
        "chunk_format_version": CHUNK_FORMAT_VERSION,
    })

    try:
        store_embeddings(collection_name, chunks)
    except Exception as e:
        raise EmbeddingError("Failed to create or store embeddings.") from e


def ingest_repository(
    url: str,
    owner: str,
    repo_name: str,
    force_reindex: bool = False,
) -> tuple[str, list[dict], str]:
    """
    Clone repo, read files, chunk, embed, and store in ChromaDB.
    Returns (collection_name, files, folder_structure).

    Caching: reuses compatible Chroma collections. Incompatible (old chunk
    format) collections are safely replaced without deleting MongoDB records.
    """
    collection_name = get_collection_name(owner, repo_name)
    repository_label = f"{owner}/{repo_name}"
    settings = get_settings()

    compatible = is_collection_compatible(collection_name)
    can_reuse = (
        not force_reindex
        and compatible
        and collection_exists(collection_name)
    )

    if can_reuse:
        clone_path = os.path.join(settings.temp_clone_dir, f"{owner}_{repo_name}")
        if not os.path.exists(clone_path):
            clone_path = clone_repository(url, owner, repo_name)
        files = read_repository_files(clone_path)
        folder_structure = get_folder_structure(clone_path)
        log_rag_event("Cache hit", {"collection": collection_name, "compatible": True})
        return collection_name, files, folder_structure

    # Incompatible old index — clear vector collection only
    if collection_exists(collection_name) and not compatible:
        log_rag_event("Re-index required", {
            "collection": collection_name,
            "reason": "incompatible_chunk_format",
            "expected": CHUNK_FORMAT_VERSION,
        })
        try:
            delete_collection(collection_name)
        except Exception as e:
            raise VectorStoreError("Failed to clear outdated vector index.") from e

    clone_path = clone_repository(url, owner, repo_name)
    try:
        files = read_repository_files(clone_path)
    except Exception as e:
        raise IngestionError("Failed to read repository source files.") from e

    if not files:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise EmptyRepositoryError("No readable source files found in this repository.")

    folder_structure = get_folder_structure(clone_path)

    try:
        _index_files(collection_name, files, repository_label)
    except (IngestionError, EmbeddingError, EmptyRepositoryError):
        raise
    except Exception as e:
        raise VectorStoreError("Failed to store repository vectors.") from e

    return collection_name, files, folder_structure


def reindex_repository(
    url: str,
    owner: str,
    repo_name: str,
) -> tuple[str, list[dict], str]:
    """
    Safely re-index: replace Chroma collection with new code-aware chunks.
    Does not touch MongoDB repository/user records.
    """
    return ingest_repository(url, owner, repo_name, force_reindex=True)


def cleanup_clone(owner: str, repo_name: str):
    settings = get_settings()
    clone_path = os.path.join(settings.temp_clone_dir, f"{owner}_{repo_name}")
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)
