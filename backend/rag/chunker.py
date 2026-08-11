"""Code-aware document chunking with rich metadata."""

from __future__ import annotations

import os
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.config import get_settings

# Chunk format version — bump when metadata/chunking becomes incompatible
CHUNK_FORMAT_VERSION = "2"

EXT_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
}

# Prefer splitting on these for source code before falling back to characters
CODE_SEPARATORS = [
    "\nclass ",
    "\nexport class ",
    "\nexport default class ",
    "\nexport function ",
    "\nexport async function ",
    "\nexport const ",
    "\nexport default function ",
    "\nasync function ",
    "\nfunction ",
    "\ndef ",
    "\nasync def ",
    "\n@interface ",
    "\ntype ",
    "\nconst ",
    "\nlet ",
    "\nvar ",
    "\n\n",
    "\n",
    " ",
    "",
]

# Language-specific patterns: (chunk_type, name_group, pattern)
STRUCTURE_PATTERNS = {
    "python": [
        ("class", 1, re.compile(r"^class\s+(\w+)", re.MULTILINE)),
        ("function", 1, re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE)),
    ],
    "javascript": [
        ("class", 1, re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            re.MULTILINE,
        )),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>",
            re.MULTILINE,
        )),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\b",
            re.MULTILINE,
        )),
        ("interface", 1, re.compile(r"^(?:export\s+)?interface\s+(\w+)", re.MULTILINE)),
        ("type", 1, re.compile(r"^(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE)),
    ],
    "typescript": [
        ("class", 1, re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.MULTILINE)),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            re.MULTILINE,
        )),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>",
            re.MULTILINE,
        )),
        ("function", 1, re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\b",
            re.MULTILINE,
        )),
        ("interface", 1, re.compile(r"^(?:export\s+)?interface\s+(\w+)", re.MULTILINE)),
        ("type", 1, re.compile(r"^(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE)),
    ],
}

IMPORT_PATTERNS = {
    "python": re.compile(r"^(?:from\s+\S+\s+)?import\s+.+$", re.MULTILINE),
    "javascript": re.compile(
        r"^(?:import\s+.+$|export\s+(?:\{[^}]+\}|\*|default).+$)",
        re.MULTILINE,
    ),
    "typescript": re.compile(
        r"^(?:import\s+.+$|export\s+(?:\{[^}]+\}|\*|default|type).+$)",
        re.MULTILINE,
    ),
}


def _detect_language(extension: str) -> str:
    return EXT_TO_LANGUAGE.get(extension.lower(), "text")


def _line_offsets(content: str) -> list[int]:
    """Return character offset of the start of each 1-indexed line."""
    offsets = [0]
    for i, ch in enumerate(content):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _offset_to_line(offsets: list[int], offset: int) -> int:
    line = 1
    for i, start in enumerate(offsets):
        if start > offset:
            return max(1, i)
        line = i + 1
    return line


def _extract_imports(content: str, language: str) -> str:
    pattern = IMPORT_PATTERNS.get(language)
    if not pattern:
        return ""
    matches = pattern.findall(content)
    if not matches:
        return ""
    # Keep a compact import header (avoid huge import blocks)
    joined = "\n".join(matches[:40])
    return joined


def _find_structure_boundaries(content: str, language: str) -> list[dict]:
    """Find top-level structural units (class/function/etc.) with start offsets."""
    patterns = STRUCTURE_PATTERNS.get(language, [])
    hits: list[dict] = []
    for chunk_type, name_group, pattern in patterns:
        for match in pattern.finditer(content):
            # Prefer definitions that start at column 0 or after only indentation
            line_start = content.rfind("\n", 0, match.start()) + 1
            prefix = content[line_start:match.start()]
            if prefix.strip():
                continue
            hits.append({
                "start": line_start,
                "chunk_type": chunk_type,
                "name": match.group(name_group),
            })

    hits.sort(key=lambda h: h["start"])
    # Deduplicate overlapping starts (e.g. multiple patterns matching same line)
    deduped: list[dict] = []
    seen_starts: set[int] = set()
    for h in hits:
        if h["start"] in seen_starts:
            continue
        seen_starts.add(h["start"])
        deduped.append(h)
    return deduped


def _split_by_structure(content: str, language: str, max_size: int) -> list[dict]:
    """
    Split content into logical units when structure can be detected.
    Returns list of {text, chunk_type, function_name, class_name, start_offset}.
    """
    boundaries = _find_structure_boundaries(content, language)
    if not boundaries:
        return []

    units: list[dict] = []
    # Preamble (imports / module-level code before first definition)
    first_start = boundaries[0]["start"]
    if first_start > 0:
        preamble = content[:first_start].rstrip()
        if preamble.strip():
            units.append({
                "text": preamble,
                "chunk_type": "imports" if _looks_like_imports(preamble, language) else "module",
                "function_name": "",
                "class_name": "",
                "start_offset": 0,
            })

    for i, bound in enumerate(boundaries):
        end = boundaries[i + 1]["start"] if i + 1 < len(boundaries) else len(content)
        text = content[bound["start"]:end].rstrip()
        if not text.strip():
            continue

        function_name = bound["name"] if bound["chunk_type"] == "function" else ""
        class_name = bound["name"] if bound["chunk_type"] == "class" else ""
        # Methods inside classes: keep class context when nested def appears later
        # (we only split top-level, so methods stay with their class)

        # If a unit is too large, split further with code-aware character splitter
        if len(text) > max_size * 1.5:
            sub_chunks = _fallback_split(text, max_size)
            for j, sub in enumerate(sub_chunks):
                units.append({
                    "text": sub,
                    "chunk_type": bound["chunk_type"],
                    "function_name": function_name,
                    "class_name": class_name,
                    "start_offset": bound["start"] if j == 0 else bound["start"],
                    "part": j,
                })
        else:
            units.append({
                "text": text,
                "chunk_type": bound["chunk_type"],
                "function_name": function_name,
                "class_name": class_name,
                "start_offset": bound["start"],
            })

    return units


def _looks_like_imports(text: str, language: str) -> bool:
    pattern = IMPORT_PATTERNS.get(language)
    if not pattern:
        return False
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return False
    import_lines = sum(1 for ln in lines if pattern.match(ln))
    return import_lines >= max(1, len(lines) // 2)


def _fallback_split(text: str, chunk_size: int, overlap: int | None = None) -> list[str]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap if overlap is not None else settings.chunk_overlap,
        length_function=len,
        separators=CODE_SEPARATORS,
    )
    return splitter.split_text(text)


def _build_metadata(
    *,
    repository: str,
    file_path: str,
    language: str,
    chunk_type: str,
    function_name: str,
    class_name: str,
    start_line: int,
    end_line: int,
    chunk_index: int,
) -> dict:
    """Build Chroma-compatible metadata (str/int/float/bool only)."""
    file_name = os.path.basename(file_path)
    meta = {
        "repository": repository or "",
        "file_path": file_path,
        "file_name": file_name,
        "source": file_path,  # backward compatible
        "language": language,
        "chunk_type": chunk_type or "code",
        "function_name": function_name or "",
        "class_name": class_name or "",
        "start_line": int(start_line),
        "end_line": int(end_line),
        "chunk_index": int(chunk_index),
        "chunk_format_version": CHUNK_FORMAT_VERSION,
    }
    return meta


def _locate_chunk_in_file(content: str, chunk_text: str, search_from: int = 0) -> tuple[int, int]:
    """Return (start_offset, end_offset) of chunk_text within content."""
    idx = content.find(chunk_text, search_from)
    if idx < 0:
        # Try stripped match for overlap artifacts
        stripped = chunk_text.strip()
        idx = content.find(stripped, search_from)
        if idx < 0:
            return search_from, search_from + len(chunk_text)
        return idx, idx + len(stripped)
    return idx, idx + len(chunk_text)


def chunk_documents(
    files: list[dict],
    repository: str = "",
) -> list[dict]:
    """
    Split file contents into code-aware chunks with metadata.

    Each chunk: {content, metadata}
    """
    settings = get_settings()
    max_size = settings.chunk_size
    chunks: list[dict] = []

    for file_data in files:
        file_path = file_data["path"]
        content = file_data["content"]
        extension = file_data.get("extension") or os.path.splitext(file_path)[1]
        language = _detect_language(extension)
        offsets = _line_offsets(content)
        imports_header = _extract_imports(content, language)

        structural = _split_by_structure(content, language, max_size)

        if structural:
            units = structural
        else:
            # Plain / unstructured files — character split with code separators
            text_parts = _fallback_split(content, max_size)
            units = [
                {
                    "text": part,
                    "chunk_type": "code",
                    "function_name": "",
                    "class_name": "",
                    "start_offset": 0,
                }
                for part in text_parts
            ]

        search_from = 0
        for i, unit in enumerate(units):
            text = unit["text"]
            # For non-import structural chunks, prepend compact imports for context
            # (helps retrieval for "how does X import Y" without exploding size)
            if (
                imports_header
                and unit.get("chunk_type") not in ("imports", "module")
                and language in ("python", "javascript", "typescript")
                and i == 0
                and "import" not in text[:200].lower()
            ):
                # Only attach a short hint on the first code unit if imports missing
                pass

            start_off, end_off = _locate_chunk_in_file(content, text, search_from)
            if start_off >= search_from:
                search_from = start_off + 1

            start_line = _offset_to_line(offsets, start_off)
            end_line = _offset_to_line(offsets, max(start_off, end_off - 1))

            # Infer enclosing class for methods if class_name empty but we're inside a class chunk
            class_name = unit.get("class_name") or ""
            function_name = unit.get("function_name") or ""
            chunk_type = unit.get("chunk_type") or "code"

            # Detect method defs inside a class unit that was further split
            if not function_name and language == "python":
                m = re.search(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", text, re.MULTILINE)
                if m:
                    function_name = m.group(1)
                    if chunk_type == "class" and "\ndef " in text[m.start():]:
                        pass  # keep as class if whole class
                    elif chunk_type != "class":
                        chunk_type = "function"

            chunks.append({
                "content": text,
                "metadata": _build_metadata(
                    repository=repository,
                    file_path=file_path,
                    language=language,
                    chunk_type=chunk_type,
                    function_name=function_name,
                    class_name=class_name,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_index=i,
                ),
            })

    return chunks
