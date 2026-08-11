"""Lightweight modular reranker for hybrid RAG candidates."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional


PATH_BOOST_KEYWORDS = {
    "auth": ["auth", "login", "jwt", "session", "password", "token", "middleware"],
    "api": ["route", "router", "api", "endpoint", "controller", "handler"],
    "frontend": ["component", "page", "jsx", "tsx", "react", "frontend", "ui", "client"],
    "backend": ["backend", "server", "service", "fastapi", "express", "flask"],
    "db": ["model", "schema", "mongo", "database", "repository", "db"],
    "config": ["config", "settings", "env", ".env"],
}


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_./\-]+", text or "") if len(t) > 1}


class BaseReranker(ABC):
    """Swap this class later for a cross-encoder or other model."""

    @abstractmethod
    def score(self, query: str, candidate: dict, query_info: Optional[dict] = None) -> float:
        ...

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        query_info: Optional[dict] = None,
        top_k: int = 5,
    ) -> list[dict]:
        scored = []
        for c in candidates:
            score = self.score(query, c, query_info)
            item = dict(c)
            item["relevance_score"] = score
            scored.append(item)
        scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return self._diversify(scored, top_k)

    def _diversify(self, ranked: list[dict], top_k: int) -> list[dict]:
        """Prefer diverse files while keeping top relevance."""
        if not ranked:
            return []
        selected: list[dict] = []
        seen_files: set[str] = set()
        for item in ranked:
            path = item.get("file_path") or item.get("source") or ""
            if path in seen_files and len(selected) < top_k:
                same_count = sum(
                    1 for s in selected
                    if (s.get("file_path") or s.get("source")) == path
                )
                if same_count >= 2:
                    continue
            selected.append(item)
            seen_files.add(path)
            if len(selected) >= top_k:
                break
        if len(selected) < top_k:
            ids = {id(s) for s in selected}
            for item in ranked:
                if id(item) in ids:
                    continue
                selected.append(item)
                if len(selected) >= top_k:
                    break
        return selected


class LightweightReranker(BaseReranker):
    """
    Practical local reranker (scores roughly in 0–1):
    - semantic similarity (from vector distance)
    - lexical/token overlap
    - exact identifier hits
    - path/metadata boosts
    """

    def score(self, query: str, candidate: dict, query_info: Optional[dict] = None) -> float:
        query_info = query_info or {}
        content = candidate.get("content") or ""
        metadata = candidate.get("metadata") or {}
        file_path = (
            candidate.get("file_path")
            or metadata.get("file_path")
            or candidate.get("source")
            or metadata.get("source")
            or ""
        ).lower()
        function_name = (
            candidate.get("function_name")
            or metadata.get("function_name")
            or ""
        ).lower()
        class_name = (
            candidate.get("class_name")
            or metadata.get("class_name")
            or ""
        ).lower()
        language = (
            candidate.get("language")
            or metadata.get("language")
            or ""
        ).lower()

        q_tokens = _tokenize(query)
        c_tokens = _tokenize(content)
        path_tokens = _tokenize(file_path.replace("/", " ").replace(".", " ").replace("_", " "))
        name_tokens = _tokenize(f"{function_name} {class_name}")

        if q_tokens:
            overlap = len(q_tokens & c_tokens) / max(len(q_tokens), 1)
            path_overlap = len(q_tokens & path_tokens) / max(len(q_tokens), 1)
            name_overlap = len(q_tokens & name_tokens) / max(len(q_tokens), 1)
        else:
            overlap = path_overlap = name_overlap = 0.0

        distance = candidate.get("distance")
        if distance is not None:
            semantic = max(0.0, min(1.0, 1.0 - float(distance)))
        else:
            semantic = float(candidate.get("semantic_score") or 0.0)

        identifier_boost = 0.0
        for ident in query_info.get("identifiers") or []:
            if not ident:
                continue
            ident_l = ident.lower()
            snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", ident).replace("-", "_").lower()

            in_content = ident in content or ident_l in content.lower() or snake in content.lower()
            if not in_content:
                if ident_l in file_path or snake in file_path or ident_l in function_name:
                    identifier_boost += 0.08
                continue

            # Prefer real code usage over string-list / docs mentions
            code_usage = re.search(
                rf"(?:settings\.|getenv\(|environ\[|os\.environ).{{0,30}}{re.escape(snake)}"
                rf"|{re.escape(snake)}\s*=\s*"
                rf"|jwt\.(?:encode|decode)\([^)]*{re.escape(snake)}",
                content,
                re.IGNORECASE,
            )
            only_quoted = (
                not code_usage
                and (
                    f'"{ident}"' in content
                    or f"'{ident}'" in content
                    or f'"{snake}"' in content
                    or f"'{snake}'" in content
                )
            )

            if code_usage:
                identifier_boost += 0.22
            elif only_quoted:
                identifier_boost += 0.04
            else:
                identifier_boost += 0.10

            if ident_l in file_path or snake in file_path or ident_l in function_name or snake in function_name:
                identifier_boost += 0.08
            if any(part in file_path for part in ("auth", "jwt", "middleware", "config")):
                identifier_boost += 0.06

        identifier_boost = min(identifier_boost, 0.40)

        path_boost = 0.0
        q_lower = query.lower()
        for _intent, keys in PATH_BOOST_KEYWORDS.items():
            if any(k in q_lower for k in keys):
                if any(k in file_path for k in keys):
                    path_boost += 0.06
        path_boost = min(path_boost, 0.18)

        lang_boost = 0.0
        if any(w in q_lower for w in ("react", "component", "jsx", "frontend", "ui")):
            if language in ("javascript", "typescript") or file_path.endswith(
                (".jsx", ".tsx", ".js", ".ts")
            ):
                lang_boost = 0.05
        if any(w in q_lower for w in ("python", "fastapi", "backend", "flask", "django")):
            if language == "python" or file_path.endswith(".py"):
                lang_boost = 0.05

        keyword_boost = 0.08 if candidate.get("from_keyword") else 0.0
        vector_boost = 0.03 if candidate.get("from_vector") else 0.0

        score = (
            0.45 * semantic
            + 0.22 * overlap
            + 0.10 * path_overlap
            + 0.08 * name_overlap
            + identifier_boost
            + path_boost
            + lang_boost
            + keyword_boost
            + vector_boost
        )
        return float(min(score, 1.0))


def get_reranker() -> BaseReranker:
    """Factory — replace return value to swap reranker implementations."""
    return LightweightReranker()
