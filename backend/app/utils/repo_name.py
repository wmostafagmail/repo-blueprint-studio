import re
from urllib.parse import urlparse
from pathlib import Path

def sanitize_repo_name(name: str) -> str:
    name = re.sub(r"\.git$", "", name, flags=re.IGNORECASE)
    name = name.strip().strip("/")
    if "/" in name:
        name = name.split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
    return name or "repository"

def repo_name_from_url(url: str) -> str:
    if not url:
        return "repository"
    url = url.strip()
    if url.startswith("git@") and ":" in url:
        tail = url.split(":", 1)[1]
        return sanitize_repo_name(tail.rsplit("/", 1)[-1])
    try:
        parsed = urlparse(url)
        if parsed.path:
            return sanitize_repo_name(parsed.path.rsplit("/", 1)[-1])
    except Exception:
        pass
    return sanitize_repo_name(Path(url).name)
