import hashlib
import shutil
import os
from git import Repo
from git.exc import GitCommandError
from utils.config import get_settings
from utils.file_reader import read_repository_files, get_folder_structure
from rag.chunker import chunk_documents
from rag.embedder import store_embeddings, collection_exists


class RepositoryCloneError(Exception):
    pass


class EmptyRepositoryError(Exception):
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
            raise RepositoryCloneError("This appears to be a private repository. Only public repositories are supported.")
        raise RepositoryCloneError(f"Failed to clone repository: {str(e)}")

    return clone_path


def ingest_repository(
    url: str,
    owner: str,
    repo_name: str,
    force_reindex: bool = False,
) -> tuple[str, list[dict], str]:
    """
    Clone repo, read files, chunk, embed, and store in ChromaDB.
    Returns (collection_name, files, folder_structure).
    """
    collection_name = get_collection_name(owner, repo_name)

    if not force_reindex and collection_exists(collection_name):
        settings = get_settings()
        clone_path = os.path.join(settings.temp_clone_dir, f"{owner}_{repo_name}")
        if not os.path.exists(clone_path):
            clone_path = clone_repository(url, owner, repo_name)
        files = read_repository_files(clone_path)
        folder_structure = get_folder_structure(clone_path)
        return collection_name, files, folder_structure

    clone_path = clone_repository(url, owner, repo_name)
    files = read_repository_files(clone_path)

    if not files:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise EmptyRepositoryError("No readable source files found in this repository.")

    folder_structure = get_folder_structure(clone_path)
    chunks = chunk_documents(files)
    store_embeddings(collection_name, chunks)

    return collection_name, files, folder_structure


def cleanup_clone(owner: str, repo_name: str):
    settings = get_settings()
    clone_path = os.path.join(settings.temp_clone_dir, f"{owner}_{repo_name}")
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)
