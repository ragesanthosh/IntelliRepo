import os
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "chroma",
    "temp_repos",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "htmlcov",
}

# Skip noisy / generated files even if extension is supported
IGNORED_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "poetry.lock",
    "Cargo.lock",
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".DS_Store",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".md",
    ".yaml",
    ".yml",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4",
    ".bin", ".pyc", ".pyo", ".class", ".o", ".a",
}


def is_binary_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            if b"\0" in chunk:
                return True
    except OSError:
        return True
    return False


def should_ignore_dir(dir_name: str) -> bool:
    return dir_name in IGNORED_DIRS or dir_name.startswith(".")


def read_repository_files(repo_path: str) -> list[dict]:
    """Read supported source files from a cloned repository."""
    files = []
    base_path = Path(repo_path).resolve()

    for root, dirs, filenames in os.walk(base_path):
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]

        for filename in filenames:
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()

            if filename in IGNORED_FILE_NAMES or filename.startswith(".env"):
                continue
            if filename.endswith(".min.js") or filename.endswith(".min.css"):
                continue
            if filename.endswith(".map"):
                continue
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if is_binary_file(file_path):
                continue

            try:
                rel_path = file_path.relative_to(base_path).as_posix()
                if ".." in rel_path:
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if not content.strip():
                    continue

                # Skip very large files (>100KB)
                if len(content) > 100_000:
                    content = content[:100_000] + "\n... [truncated]"

                files.append({
                    "path": rel_path,
                    "content": content,
                    "extension": ext,
                })
            except (OSError, UnicodeDecodeError):
                continue

    return files


def get_folder_structure(repo_path: str, max_depth: int = 3) -> str:
    """Generate a text representation of the folder structure."""
    lines = []
    base_path = Path(repo_path).resolve()

    def walk(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and not should_ignore_dir(e.name)]
        files = [e for e in entries if e.is_file() and e.suffix.lower() in SUPPORTED_EXTENSIONS]

        for i, d in enumerate(dirs):
            is_last = i == len(dirs) - 1 and not files
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d.name}/")
            extension = "    " if is_last else "│   "
            walk(d, prefix + extension, depth + 1)

        for i, f in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{f.name}")

    lines.append(base_path.name + "/")
    walk(base_path)
    return "\n".join(lines[:200])
