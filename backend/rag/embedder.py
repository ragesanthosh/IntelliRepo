import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from utils.config import get_settings

_model: SentenceTransformer | None = None
_chroma_client: chromadb.ClientAPI | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def store_embeddings(collection_name: str, chunks: list[dict]) -> str:
    """Store chunks and their embeddings in ChromaDB."""
    client = get_chroma_client()

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(name=collection_name)

    if not chunks:
        return collection_name

    texts = [c["content"] for c in chunks]
    embeddings = generate_embeddings(texts)
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [c["metadata"] for c in chunks]

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        collection.add(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )

    return collection_name


def collection_exists(collection_name: str) -> bool:
    client = get_chroma_client()
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False
