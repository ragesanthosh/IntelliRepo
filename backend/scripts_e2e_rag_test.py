"""
E2E chat test against a locally indexed IntelliRepo backend snapshot.
Tests auth + chat RAG without requiring a fresh Gemini repository analysis.
"""
from __future__ import annotations

import os
import sys
import time

import httpx
from bson import ObjectId
from pymongo import MongoClient

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from utils.file_reader import read_repository_files
from rag.chunker import chunk_documents
from rag.embedder import store_embeddings, delete_collection
from rag.ingestor import get_collection_name

BASE = "http://127.0.0.1:8000/api"
EMAIL = f"ragtest_{int(time.time())}@example.com"
PASSWORD = "TestPass123!"
OWNER = "local"
REPO_NAME = "intellirepo_rag_e2e"


def seed_index_and_mongo(user_id: str) -> str:
    collection_name = get_collection_name(OWNER, REPO_NAME)
    files = [
        f for f in read_repository_files(ROOT)
        if "scripts_" not in f["path"]
    ]
    project_root = os.path.dirname(ROOT)
    fe = os.path.join(project_root, "frontend", "src")
    if os.path.isdir(fe):
        files.extend(read_repository_files(fe))

    chunks = chunk_documents(files, repository=f"{OWNER}/{REPO_NAME}")
    delete_collection(collection_name)
    store_embeddings(collection_name, chunks)
    print(f"Indexed {len(files)} files / {len(chunks)} chunks -> {collection_name}")

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DATABASE_NAME", "IntelliRepo")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    doc = {
        "userId": user_id,
        "repositoryName": REPO_NAME,
        "repositoryUrl": f"https://github.com/{OWNER}/{REPO_NAME}",
        "owner": OWNER,
        "summary": {
            "project_summary": "IntelliRepo is a GitHub repository AI analyzer with JWT auth, FastAPI backend, React frontend, ChromaDB RAG, and Gemini.",
            "how_it_works": "Users register/login, analyze repos, then chat via RAG.",
            "architecture": {
                "folder_structure": "backend and frontend",
                "main_folders": [{"name": "backend", "responsibility": "API"}, {"name": "frontend", "responsibility": "UI"}],
                "important_files": ["backend/auth/jwt_handler.py", "backend/routes/auth_routes.py"],
            },
            "important_files": [
                {
                    "file_name": "backend/auth/jwt_handler.py",
                    "purpose": "JWT create/decode",
                    "importance": "auth",
                    "explanation": "Uses jwt_secret",
                }
            ],
            "technology_stack": [
                {"name": "FastAPI", "reason": "API"},
                {"name": "React", "reason": "UI"},
                {"name": "MongoDB", "reason": "persistence"},
            ],
            "ai_insights": {
                "complexity": "Medium",
                "code_quality": "Good",
                "strengths": ["modular"],
                "weaknesses": ["none"],
                "improvements": ["streaming"],
            },
        },
        "chromaCollection": collection_name,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    result = db["repositories"].insert_one(doc)
    return str(result.inserted_id)


def main():
    client = httpx.Client(timeout=120.0)

    r = client.post(f"{BASE}/auth/register", json={
        "name": "RAG Tester", "email": EMAIL, "password": PASSWORD,
    })
    r.raise_for_status()
    print("OK register")

    r = client.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("OK login")

    r = client.get(f"{BASE}/auth/me", headers=headers)
    r.raise_for_status()
    user_id = r.json()["id"]
    print("OK me", user_id)

    repo_id = seed_index_and_mongo(user_id)
    print("OK seeded repo", repo_id)

    r = client.post(f"{BASE}/chat/{repo_id}/conversations", headers=headers)
    r.raise_for_status()
    conv_id = r.json()["id"]
    print("OK conversation", conv_id)

    scenarios = [
        ("How does authentication work?", True),
        ("How does login work?", True),
        ("Where is JWT_SECRET used?", True),
        ("Where is the login controller?", True),
        ("What about the middleware?", True),
        ("Explain the complete login flow from frontend to backend.", True),
        ("How does the frontend communicate with the backend?", True),
        ("Does this project use Kafka?", False),
    ]

    for q, expect_answerable in scenarios:
        print("\n===", q)
        r = client.post(
            f"{BASE}/chat/message",
            headers=headers,
            json={
                "repository_id": repo_id,
                "conversation_id": conv_id,
                "message": q,
            },
            timeout=120.0,
        )
        if r.status_code >= 400:
            print("HTTP FAIL", r.status_code, r.text[:400])
            continue
        body = r.json()
        answer = body.get("answer") or ""
        sources = body.get("sources") or []
        print("sources:", sources)
        print("answer:", answer[:350].replace("\n", " "))

        insufficient = "couldn't find enough relevant information" in answer.lower()
        if expect_answerable and insufficient:
            print("WARN: expected answerable but got insufficient evidence")
        if not expect_answerable and not insufficient:
            # Gemini may say "no kafka" which is fine
            if "kafka" in answer.lower() and all(
                w not in answer.lower() for w in ("not", "no ", "don't", "couldn't", "does not", "doesn't")
            ):
                print("FAIL: possible Kafka hallucination")
            else:
                print("OK: unanswerable handled without claiming Kafka exists")

    print("\nE2E chat test finished.")


if __name__ == "__main__":
    main()
