import re
from urllib.parse import urlparse


GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$"
)


def parse_github_url(url: str) -> tuple[str, str, str] | None:
    """Parse GitHub URL and return (owner, repo_name, normalized_url) or None."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        return None

    owner, repo_name = match.group(1), match.group(2)
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    normalized = f"https://github.com/{owner}/{repo_name}"
    return owner, repo_name, normalized


def is_valid_github_url(url: str) -> bool:
    return parse_github_url(url) is not None
