"""
Offline RAG smoke test — indexes backend/frontend source and runs retrieval scenarios.
Does not call Gemini (retrieval-only). Excludes this script from the index.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.file_reader import read_repository_files
from rag.chunker import chunk_documents, CHUNK_FORMAT_VERSION
from rag.embedder import store_embeddings, is_collection_compatible, delete_collection
from rag.retriever import retrieve_relevant_chunks
from rag.query import rewrite_query_for_retrieval


COLLECTION = "repo_smoke_intellirepo_rag"
SELF_NAME = os.path.basename(__file__)


def main():
    backend_root = ROOT
    project_root = os.path.dirname(backend_root)

    files = [
        f for f in read_repository_files(backend_root)
        if not f["path"].endswith(SELF_NAME)
        and "scripts_rag_smoke_test" not in f["path"]
    ]
    frontend_src = os.path.join(project_root, "frontend", "src")
    if os.path.isdir(frontend_src):
        files.extend(read_repository_files(frontend_src))

    print(f"Files indexed: {len(files)}")
    chunks = chunk_documents(files, repository="intellirepo/local")
    print(f"Chunks: {len(chunks)} (format v{CHUNK_FORMAT_VERSION})")
    assert chunks, "No chunks produced"

    authish = [
        c for c in chunks
        if "auth" in (c["metadata"].get("file_path") or "").lower()
        or "login" in (c["metadata"].get("file_path") or "").lower()
    ]
    print(f"Auth-related chunks: {len(authish)}")

    delete_collection(COLLECTION)
    store_embeddings(COLLECTION, chunks)
    assert is_collection_compatible(COLLECTION), "Collection format mismatch"

    scenarios = [
        ("How does authentication work?", None, True),
        ("How does login work?", None, True),
        ("Where is JWT_SECRET used?", None, True),
        ("Where is the login controller?", None, True),
        ("Explain the complete login flow from frontend to backend.", None, True),
        ("How does the frontend communicate with the backend?", None, True),
        ("Does this project use Kafka?", None, False),
        (
            "What about the middleware?",
            [{"role": "user", "content": "How does authentication work?"}],
            True,
        ),
    ]

    failures = []
    for question, history, expect_sufficient in scenarios:
        qinfo = rewrite_query_for_retrieval(question, history=history)
        result = retrieve_relevant_chunks(COLLECTION, question, history=history)
        print("\n" + "=" * 60)
        print(f"Q: {question}")
        print(f"Rewritten: {qinfo['rewritten'][:140]}")
        print(f"sufficient={result['sufficient']} confidence={result['confidence']:.3f} expected={expect_sufficient}")
        print(f"sources={result['sources']}")
        for c in result["chunks"][:3]:
            print(
                f"  - {c.get('file_path')} "
                f"score={c.get('relevance_score', 0):.3f} "
                f"fn={c.get('function_name') or '-'}"
            )
        if result["sufficient"] != expect_sufficient:
            failures.append(question)

    if failures:
        print("\nFAILED scenarios:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
