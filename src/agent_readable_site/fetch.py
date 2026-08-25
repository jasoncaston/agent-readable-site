"""URL fetching with explicit missing and unreadable states."""

from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse, urlunparse
from urllib.request import Request, urlopen


USER_AGENT = "agent-readable-site/0.1 (+https://llmstxt.org/)"


class FetchFailure(RuntimeError):
    """A resource could not be read reliably."""


class ResourceMissing(FetchFailure):
    """A resource returned a definite not-found result."""


def fetch_text(url: str, timeout: float = 10.0) -> str:
    """Fetch UTF-8-oriented text from HTTP, HTTPS, or a local file URL."""

    parsed = urlparse(url)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path))
        if not path.is_file():
            raise ResourceMissing(f"resource not found: {url}")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise FetchFailure(f"could not read {url}: {exc}") from exc
        if not raw:
            raise FetchFailure(f"resource was empty: {url}")
        return raw.decode("utf-8", errors="strict")

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FetchFailure(f"unsupported or incomplete URL: {url}")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except HTTPError as exc:
        if exc.code == 404:
            raise ResourceMissing(f"resource not found: {url}") from exc
        raise FetchFailure(f"fetch failed for {url}: HTTP {exc.code}") from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise FetchFailure(f"fetch failed for {url}: {exc}") from exc

    if not raw:
        raise FetchFailure(f"resource was empty: {url}")
    try:
        return raw.decode(charset, errors="strict")
    except (LookupError, UnicodeDecodeError) as exc:
        raise FetchFailure(f"could not decode {url} as {charset}: {exc}") from exc


def root_resource_url(page_url: str, filename: str) -> str:
    """Return a root resource URL for a page URL."""

    parsed = urlparse(page_url)
    if parsed.scheme == "file":
        page_path = Path(unquote(parsed.path))
        return (page_path.parent / filename).resolve().as_uri()
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return urlunparse((parsed.scheme, parsed.netloc, f"/{filename}", "", "", ""))
    raise FetchFailure(f"unsupported or incomplete URL: {page_url}")
