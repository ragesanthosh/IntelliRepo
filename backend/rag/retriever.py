from rag.embedder import get_chroma_client, generate_embeddings


def retrieve_relevant_chunks(
    collection_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve the most relevant chunks for a query."""
    client = get_chroma_client()

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    query_embedding = generate_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 1.0
            chunks.append({
                "content": doc,
                "source": metadata.get("source", "unknown"),
                "distance": distance,
            })

    return chunks
