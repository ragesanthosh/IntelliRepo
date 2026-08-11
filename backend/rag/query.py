"""Query understanding: conversation resolution + retrieval query rewriting."""

from __future__ import annotations

import re
from typing import Optional

# Concept expansions for common developer questions (retrieval-only)
CONCEPT_EXPANSIONS: dict[str, list[str]] = {
    "login": [
        "authentication", "auth", "signin", "sign-in", "login route",
        "login controller", "loginUser", "JWT", "session", "credentials",
        "password", "middleware", "frontend login", "API login",
    ],
    "authentication": [
        "auth", "login", "JWT", "token", "middleware", "authorize",
        "authorization", "session", "bcrypt", "password", "bearer",
        "authMiddleware", "protected route",
    ],
    "auth": [
        "authentication", "authorization", "login", "JWT", "middleware",
        "token", "session", "bearer",
    ],
    "jwt": [
        "JSON Web Token", "token", "Bearer", "jwt_secret", "JWT_SECRET",
        "sign", "verify", "decode", "auth middleware", "access token",
    ],
    "middleware": [
        "middleware", "authMiddleware", "interceptor", "guard",
        "request handler", "next()", "protect", "verify token",
    ],
    "register": [
        "signup", "sign-up", "registration", "create user", "registerUser",
        "auth route", "password hash", "bcrypt",
    ],
    "api": [
        "route", "endpoint", "controller", "router", "REST", "request",
        "response", "axios", "fetch", "API call",
    ],
    "database": [
        "mongodb", "mongo", "schema", "model", "collection", "query",
        "pymongo", "mongoose", "ORM", "repository",
    ],
    "frontend": [
        "react", "component", "page", "UI", "jsx", "tsx", "vite",
        "axios", "fetch", "client",
    ],
    "backend": [
        "server", "api", "route", "controller", "service", "fastapi",
        "express", "flask", "django",
    ],
    "cors": ["CORS", "cross-origin", "Access-Control", "middleware"],
    "error": ["exception", "try catch", "HTTPException", "error handler", "status"],
    "config": ["settings", "environment", ".env", "config", "configuration"],
    "chat": ["conversation", "message", "RAG", "gemini", "assistant"],
    "embedding": ["vector", "chroma", "sentence transformer", "embed"],
    "clone": ["git", "repository", "GitPython", "ingest"],
}

FOLLOWUP_PATTERNS = re.compile(
    r"\b(what about|how about|and the|tell me more|explain (?:it|that|this)|"
    r"where is (?:it|that|this)|what does (?:it|that|this)|"
    r"\b(?:it|that|this|them|those)\b|"
    r"the (?:middleware|controller|route|function|file|component|class|api|endpoint))\b",
    re.IGNORECASE,
)

IDENTIFIER_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]{2,}|[a-zA-Z_][a-zA-Z0-9_]*(?:Middleware|Controller|Service|Router|Schema|Model|Handler|Provider)?|[a-z]+(?:[A-Z][a-zA-Z0-9_]+)+|/api/[a-zA-Z0-9_/\-]+)\b"
)

PATH_HINT_RE = re.compile(
    r"\b([\w\-]+/[\w\-./]+\.\w{1,10}|[\w\-]+\.(?:py|js|jsx|ts|tsx|json|md))\b"
)


def _recent_user_topics(history: list[dict] | None, max_turns: int = 4) -> str:
    if not history:
        return ""
    parts = []
    for msg in history[-max_turns * 2 :]:
        if msg.get("role") == "user":
            parts.append(msg.get("content", ""))
    return " ".join(parts)


def resolve_followup_question(
    question: str,
    history: list[dict] | None = None,
) -> str:
    """
    Resolve vague follow-ups using recent conversation context.
    Returns a standalone question for retrieval (not shown to the user).
    """
    q = (question or "").strip()
    if not q or not history:
        return q

    if not FOLLOWUP_PATTERNS.search(q) and len(q.split()) > 6:
        return q

    prior = _recent_user_topics(history, max_turns=3)
    if not prior:
        return q

    # Lightweight merge: attach prior topic terms without duplicating the full history
    prior_terms = _extract_key_terms(prior)
    current_lower = q.lower()
    missing = [t for t in prior_terms if t.lower() not in current_lower]
    if not missing:
        return q

    return f"{q} (context: {' '.join(missing[:12])})"


def _extract_key_terms(text: str) -> list[str]:
    stop = {
        "how", "does", "what", "where", "when", "why", "the", "a", "an", "is",
        "are", "in", "of", "to", "for", "and", "or", "with", "this", "that",
        "it", "about", "work", "works", "explain", "tell", "me", "please",
        "can", "you", "from", "complete", "flow",
    }
    terms = []
    for token in re.findall(r"[A-Za-z_][A-Za-z0-9_/\-]{2,}", text):
        if token.lower() in stop:
            continue
        if token not in terms:
            terms.append(token)
    return terms[:20]


def extract_identifiers(question: str) -> list[str]:
    """Extract code-like identifiers and path hints from the question."""
    found: list[str] = []
    for match in IDENTIFIER_RE.finditer(question or ""):
        token = match.group(1)
        if token.lower() in {"how", "does", "what", "where", "when", "this", "that"}:
            continue
        if token not in found:
            found.append(token)
    for match in PATH_HINT_RE.finditer(question or ""):
        token = match.group(1)
        if token not in found:
            found.append(token)
    # Quoted strings often are exact identifiers
    for match in re.finditer(r"['\"`]([A-Za-z0-9_./\-]+)['\"`]", question or ""):
        token = match.group(1)
        if token not in found:
            found.append(token)

    # Add snake_case variants for ENV-style names (JWT_SECRET → jwt_secret)
    variants: list[str] = []
    for token in found:
        lower = token.lower()
        if lower not in found and lower not in variants:
            variants.append(lower)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", token).replace("-", "_").lower()
        if snake not in found and snake not in variants:
            variants.append(snake)
    found.extend(variants)
    return found


def extract_required_terms(question: str) -> list[str]:
    """
    Distinctive terms that should appear in evidence for factual/tech questions.
    e.g. 'Does this project use SomeBroker?' → ['SomeBroker']
    """
    q = question or ""
    required: list[str] = []

    # Explicit "use/using X" patterns
    for match in re.finditer(
        r"\b(?:use|uses|using|support|supports|have|has|include|includes)\s+([A-Z][A-Za-z0-9_.\-]+)\b",
        q,
    ):
        required.append(match.group(1))

    # Standalone tech-like tokens
    for match in re.finditer(r"\b([A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)*|[A-Z]{3,})\b", q):
        token = match.group(1)
        if token.upper() in {
            "JWT", "API", "URL", "HTTP", "HTTPS", "JSON", "HTML", "CSS", "SQL",
            "RAG", "AI", "UI", "CLI", "SDK", "ORM", "REST", "CRUD",
        }:
            continue
        if token.lower() in {
            "how", "what", "where", "when", "why", "does", "this", "that",
            "explain", "complete", "frontend", "backend", "project",
        }:
            continue
        if token not in required:
            required.append(token)

    return required


def expand_concepts(question: str) -> list[str]:
    """Return related concept terms for the question."""
    lower = (question or "").lower()
    expanded: list[str] = []
    for key, values in CONCEPT_EXPANSIONS.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            for v in values:
                if v.lower() not in lower and v not in expanded:
                    expanded.append(v)
    return expanded


def rewrite_query_for_retrieval(
    question: str,
    history: list[dict] | None = None,
    extra_terms: Optional[list[str]] = None,
) -> dict:
    """
    Build a retrieval-oriented query from the user question.

    Returns:
      {
        original, resolved, rewritten, identifiers, concepts, path_hints
      }
    """
    original = (question or "").strip()
    resolved = resolve_followup_question(original, history)
    identifiers = extract_identifiers(resolved)
    concepts = expand_concepts(resolved)
    path_hints = PATH_HINT_RE.findall(resolved)

    parts = [resolved]
    if concepts:
        parts.append(" ".join(concepts[:16]))
    if identifiers:
        parts.append(" ".join(identifiers[:10]))
    if extra_terms:
        parts.append(" ".join(extra_terms[:10]))

    # Deduplicate whitespace
    rewritten = " ".join(parts)
    rewritten = re.sub(r"\s+", " ", rewritten).strip()

    required_terms = extract_required_terms(resolved)

    return {
        "original": original,
        "resolved": resolved,
        "rewritten": rewritten,
        "identifiers": identifiers,
        "concepts": concepts,
        "path_hints": path_hints,
        "required_terms": required_terms,
    }


def expand_query_for_retry(query_info: dict) -> dict:
    """Broader rewrite used when first retrieval lacks confidence."""
    extra = [
        "implementation", "source code", "handler", "service", "route",
        "controller", "component", "config", "utils", "helper",
    ]
    base = query_info.get("resolved") or query_info.get("original") or ""
    return rewrite_query_for_retrieval(base, extra_terms=extra + query_info.get("concepts", []))
