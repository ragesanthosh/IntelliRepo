"""RAG debug logging (never logs secrets)."""

from __future__ import annotations

import logging
from utils.config import get_settings

logger = logging.getLogger("intellirepo.rag")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[RAG_DEBUG] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

_SECRET_KEYS = {
    "gemini_api_key", "jwt_secret", "mongodb_uri", "password", "token",
    "authorization", "api_key", "secret",
}


def rag_debug_enabled() -> bool:
    return bool(get_settings().rag_debug)


def _safe_preview(text: str, limit: int = 160) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")


def _chunk_summary(chunk: dict) -> str:
    path = chunk.get("file_path") or chunk.get("source") or "?"
    score = chunk.get("relevance_score")
    dist = chunk.get("distance")
    parts = [path]
    if score is not None:
        parts.append(f"score={score:.3f}")
    if dist is not None:
        parts.append(f"dist={float(dist):.3f}")
    fn = chunk.get("function_name") or (chunk.get("metadata") or {}).get("function_name")
    if fn:
        parts.append(f"fn={fn}")
    return " | ".join(parts)


def log_rag_event(title: str, payload: dict | list | str | None = None):
    if not rag_debug_enabled():
        return
    if isinstance(payload, dict):
        # Strip anything that looks secret
        safe = {
            k: v for k, v in payload.items()
            if k.lower() not in _SECRET_KEYS and "secret" not in k.lower() and "password" not in k.lower()
        }
        logger.info("%s: %s", title, safe)
    elif isinstance(payload, list):
        if payload and isinstance(payload[0], dict):
            logger.info("%s (%d):", title, len(payload))
            for i, item in enumerate(payload[:20]):
                logger.info("  [%d] %s :: %s", i, _chunk_summary(item), _safe_preview(item.get("content", "")))
        else:
            logger.info("%s: %s", title, payload)
    else:
        logger.info("%s: %s", title, payload)
