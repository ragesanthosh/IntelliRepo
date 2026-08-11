"""Hybrid RAG retrieval: semantic + keyword + metadata + rerank + confidence."""

from __future__ import annotations

import re
from typing import Optional

from rag.embedder import get_chroma_client, generate_embeddings
from rag.query import rewrite_query_for_retrieval, expand_query_for_retry
from rag.reranker import get_reranker
from rag.debug import log_rag_event
from utils.config import get_settings


class RetrievalError(Exception):
    """Infrastructure failure during retrieval (not 'no results')."""


def _chunks_contain_term(chunks: list[dict], term: str) -> bool:
    term_l = (term or "").lower()
    if not term_l:
        return True
    neg_patterns = [
        rf"(?:do not|don't|never|not)\b.{{0,60}}{re.escape(term_l)}",
        rf"(?:e\.g\.|eg\.|example|invent|unless).{{0,40}}{re.escape(term_l)}",
        rf"{re.escape(term_l)}.{{0,40}}(?:unless|invent|hallucin)",
    ]
    for c in chunks:
        hay = " ".join([
            c.get("content") or "",
            c.get("file_path") or "",
            c.get("function_name") or "",
            c.get("class_name") or "",
        ])
        hay_l = hay.lower()
        if term_l not in hay_l:
            continue
        # Ignore purely negative / instructional mentions
        if any(re.search(p, hay_l) for p in neg_patterns):
            # Still accept if there is a clear positive code usage elsewhere in chunk
            # e.g. import or dependency style
            positive = re.search(
                rf"(?:import|from|require|include|depends).{{0,40}}{re.escape(term_l)}"
                rf"|{re.escape(term_l)}\s*=",
                hay_l,
            )
            if not positive:
                continue
        return True
    return False


def _grounding_ok(query_info: dict, chunks: list[dict]) -> bool:
    """Fail closed when distinctive required terms are absent from evidence."""
    required = query_info.get("required_terms") or []
    if not required:
        return True
    if not chunks:
        return False
    # All required distinctive terms must appear somewhere in selected evidence
    return all(_chunks_contain_term(chunks, t) for t in required)

def _normalize_chunk(
    doc: str,
    metadata: dict | None,
    *,
    distance: float | None = None,
    from_vector: bool = False,
    from_keyword: bool = False,
    chunk_id: str | None = None,
) -> dict:
    metadata = metadata or {}
    file_path = metadata.get("file_path") or metadata.get("source") or "unknown"
    return {
        "id": chunk_id or f"{file_path}:{metadata.get('chunk_index', 0)}:{metadata.get('start_line', 0)}",
        "content": doc,
        "metadata": metadata,
        "source": file_path,
        "file_path": file_path,
        "file_name": metadata.get("file_name") or file_path.split("/")[-1],
        "language": metadata.get("language") or "",
        "chunk_type": metadata.get("chunk_type") or "",
        "function_name": metadata.get("function_name") or "",
        "class_name": metadata.get("class_name") or "",
        "start_line": metadata.get("start_line"),
        "end_line": metadata.get("end_line"),
        "distance": distance,
        "from_vector": from_vector,
        "from_keyword": from_keyword,
    }


def _chunk_key(chunk: dict) -> str:
    """Deduplicate by file + line range + content fingerprint."""
    path = chunk.get("file_path") or chunk.get("source") or ""
    start = chunk.get("start_line") or 0
    end = chunk.get("end_line") or 0
    content = chunk.get("content") or ""
    fingerprint = content[:120]
    return f"{path}|{start}|{end}|{fingerprint}"


def _merge_candidates(*groups: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for group in groups:
        for chunk in group:
            key = _chunk_key(chunk)
            if key not in merged:
                merged[key] = chunk
            else:
                existing = merged[key]
                existing["from_vector"] = existing.get("from_vector") or chunk.get("from_vector")
                existing["from_keyword"] = existing.get("from_keyword") or chunk.get("from_keyword")
                # Keep better (lower) distance if available
                d_new = chunk.get("distance")
                d_old = existing.get("distance")
                if d_new is not None and (d_old is None or d_new < d_old):
                    existing["distance"] = d_new
    return list(merged.values())


def _remove_overlapping(chunks: list[dict]) -> list[dict]:
    """Drop highly overlapping chunks from the same file."""
    if not chunks:
        return []
    kept: list[dict] = []
    for chunk in chunks:
        path = chunk.get("file_path") or chunk.get("source")
        start = chunk.get("start_line")
        end = chunk.get("end_line")
        content = chunk.get("content") or ""
        duplicate = False
        for other in kept:
            if (other.get("file_path") or other.get("source")) != path:
                continue
            o_start = other.get("start_line")
            o_end = other.get("end_line")
            if start is not None and end is not None and o_start is not None and o_end is not None:
                # Overlap ratio by line range
                overlap = max(0, min(end, o_end) - max(start, o_start) + 1)
                span = max(end, o_end) - min(start, o_start) + 1
                if span > 0 and overlap / span >= 0.7:
                    duplicate = True
                    break
            else:
                # Content similarity heuristic
                a, b = content[:400], (other.get("content") or "")[:400]
                if a and b and (a in b or b in a):
                    duplicate = True
                    break
        if not duplicate:
            kept.append(chunk)
    return kept


def semantic_search(
    collection,
    query: str,
    top_k: int,
) -> list[dict]:
    count = collection.count() or 0
    if count == 0:
        return []
    n = min(top_k, count)
    query_embedding = generate_embeddings([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    if results and results["documents"] and results["documents"][0]:
        ids = results.get("ids", [[]])[0] if results.get("ids") else []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 1.0
            chunk_id = ids[i] if i < len(ids) else None
            chunks.append(
                _normalize_chunk(
                    doc,
                    metadata,
                    distance=distance,
                    from_vector=True,
                    chunk_id=chunk_id,
                )
            )
    return chunks


def keyword_search(
    collection,
    terms: list[str],
    top_k: int,
) -> list[dict]:
    """Exact/substring document search for code identifiers and keywords."""
    if not terms:
        return []
    chunks: list[dict] = []
    seen: set[str] = set()
    count = collection.count() or 0
    if count == 0:
        return []

    # Prefer longer / more specific terms first
    ordered = sorted({t for t in terms if t and len(t) >= 2}, key=len, reverse=True)

    for term in ordered[:12]:
        try:
            results = collection.get(
                where_document={"$contains": term},
                include=["documents", "metadatas"],
                limit=min(top_k, 30),
            )
        except Exception:
            # Older Chroma may not support limit on get — retry without
            try:
                results = collection.get(
                    where_document={"$contains": term},
                    include=["documents", "metadatas"],
                )
            except Exception:
                continue

        docs = results.get("documents") or []
        metas = results.get("metadatas") or []
        ids = results.get("ids") or []
        for i, doc in enumerate(docs[:top_k]):
            meta = metas[i] if i < len(metas) else {}
            chunk_id = ids[i] if i < len(ids) else None
            chunk = _normalize_chunk(
                doc,
                meta,
                distance=None,
                from_keyword=True,
                chunk_id=chunk_id,
            )
            # Soft distance so keyword hits participate in semantic blend
            # Higher for exact-ish matches in smaller chunks
            term_count = doc.count(term) if term in doc else doc.lower().count(term.lower())
            chunk["distance"] = max(0.05, 0.45 - min(term_count, 5) * 0.05)
            key = _chunk_key(chunk)
            if key not in seen:
                seen.add(key)
                chunks.append(chunk)
            if len(chunks) >= top_k * 2:
                break
        if len(chunks) >= top_k * 2:
            break

    return chunks[: top_k * 2]


def metadata_path_search(
    collection,
    path_hints: list[str],
    concept_terms: list[str],
    top_k: int,
) -> list[dict]:
    """Boost retrieval using file path / name metadata signals via keyword contains."""
    hints = []
    for h in path_hints:
        if h:
            hints.append(h)
    # Path-ish concept words
    for t in concept_terms:
        tl = t.lower()
        if any(k in tl for k in ("auth", "login", "route", "middleware", "controller", "jwt", "api")):
            hints.append(t)
    # Use unique short path fragments
    unique = []
    for h in hints:
        frag = h.split("/")[-1] if "/" in h else h
        if frag and frag not in unique:
            unique.append(frag)
    return keyword_search(collection, unique[:8], top_k=top_k)


def _confidence(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    scores = [float(c.get("relevance_score") or 0.0) for c in chunks]
    top = scores[0]
    avg_top3 = sum(scores[:3]) / max(1, min(3, len(scores)))
    return 0.6 * top + 0.4 * avg_top3


def retrieve_relevant_chunks(
    collection_name: str,
    query: str,
    top_k: int | None = None,
    history: list[dict] | None = None,
    candidate_k: int | None = None,
) -> dict:
    """
    Full hybrid retrieval pipeline.

    Returns:
      {
        chunks: list[dict],          # final selected chunks for Gemini
        sources: list[str],
        confidence: float,
        sufficient: bool,
        query_info: dict,
        fallback_message: str | None,
      }
    """
    settings = get_settings()
    final_k = top_k or settings.rag_final_k
    pool_k = candidate_k or settings.rag_candidate_k
    keyword_k = settings.rag_keyword_k
    min_relevance = settings.rag_min_relevance

    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        raise RetrievalError("Vector store collection not found for this repository.") from e

    query_info = rewrite_query_for_retrieval(query, history=history)
    log_rag_event("Original Query", query_info["original"])
    log_rag_event("Rewritten Query", query_info["rewritten"])

    try:
        vector_hits = semantic_search(collection, query_info["rewritten"], top_k=pool_k)
        # Also search with resolved question alone for precision
        if query_info["resolved"] != query_info["rewritten"]:
            vector_hits = _merge_candidates(
                vector_hits,
                semantic_search(collection, query_info["resolved"], top_k=max(4, pool_k // 2)),
            )

        keyword_terms = list(dict.fromkeys(
            query_info["identifiers"]
            + query_info["concepts"][:8]
            + [t for t in query_info["resolved"].split() if len(t) > 3][:6]
        ))
        keyword_hits = keyword_search(collection, keyword_terms, top_k=keyword_k)
        meta_hits = metadata_path_search(
            collection,
            query_info.get("path_hints") or [],
            query_info.get("concepts") or [],
            top_k=max(4, keyword_k // 2),
        )
    except RetrievalError:
        raise
    except Exception as e:
        raise RetrievalError("Failed to search repository index.") from e

    log_rag_event("Vector Results", vector_hits)
    log_rag_event("Keyword Results", keyword_hits)

    merged = _merge_candidates(vector_hits, keyword_hits, meta_hits)
    log_rag_event("Merged Candidates", merged)

    reranker = get_reranker()
    ranked = reranker.rerank(
        query=query_info["resolved"],
        candidates=merged,
        query_info=query_info,
        top_k=min(pool_k, max(final_k * 2, final_k)),
    )
    ranked = _remove_overlapping(ranked)
    log_rag_event("Reranked Candidates", ranked)

    selected = ranked[:final_k]
    confidence = _confidence(selected)
    log_rag_event("Final Selected Chunks", selected)
    log_rag_event("Relevance Scores", {
        "confidence": confidence,
        "scores": [c.get("relevance_score") for c in selected],
    })

    # Retry / expand if weak
    if confidence < min_relevance or len(selected) < max(2, final_k // 2):
        log_rag_event("Confidence Check", "insufficient — expanding query and retrying")
        expanded = expand_query_for_retry(query_info)
        try:
            more_vector = semantic_search(collection, expanded["rewritten"], top_k=pool_k)
            more_keyword = keyword_search(
                collection,
                list(dict.fromkeys(expanded["identifiers"] + expanded["concepts"][:12])),
                top_k=keyword_k,
            )
            merged2 = _merge_candidates(merged, more_vector, more_keyword)
            ranked2 = reranker.rerank(
                query=expanded["resolved"],
                candidates=merged2,
                query_info=expanded,
                top_k=min(pool_k, max(final_k * 2, final_k)),
            )
            ranked2 = _remove_overlapping(ranked2)
            selected = ranked2[:final_k]
            confidence = _confidence(selected)
            query_info = expanded
            log_rag_event("Retry Final Chunks", selected)
            log_rag_event("Retry Confidence", confidence)
        except Exception:
            pass

    sufficient = confidence >= min_relevance and len(selected) > 0

    # Soften: if we have any keyword/vector hits with some score, allow answer
    if not sufficient and selected:
        best = float(selected[0].get("relevance_score") or 0)
        if best >= min_relevance * 0.7 and (
            selected[0].get("from_keyword") or selected[0].get("from_vector")
        ):
            sufficient = True

    # Grounding gate for distinctive tech/identifier questions (e.g. Kafka)
    if sufficient and not _grounding_ok(query_info, selected):
        log_rag_event("Grounding Check", {
            "required_terms": query_info.get("required_terms"),
            "result": "failed",
        })
        sufficient = False
        selected = []
        confidence = min(confidence, min_relevance * 0.5)
    sources = []
    for c in selected:
        path = c.get("file_path") or c.get("source")
        if path and path not in sources:
            sources.append(path)

    fallback = None
    if not sufficient:
        fallback = (
            "I couldn't find enough relevant information in the repository "
            "to answer this confidently."
        )
        selected = []
        sources = []

    return {
        "chunks": selected,
        "sources": sources,
        "confidence": confidence,
        "sufficient": sufficient,
        "query_info": query_info,
        "fallback_message": fallback,
    }


# Backward-compatible wrapper used by older call sites
def retrieve_relevant_chunks_simple(
    collection_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    result = retrieve_relevant_chunks(collection_name, query, top_k=top_k)
    return result.get("chunks") or []
