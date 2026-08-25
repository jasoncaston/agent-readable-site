"""Validation and drafting for the llms.txt v2 proposal."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .fetch import FetchFailure, fetch_text
from .html_analysis import PageData, parse_html


H1 = re.compile(r"^#\s+\S")
H2 = re.compile(r"^##\s+\S")
ANY_HEADING = re.compile(r"^#{1,6}\s+")
LINK_ITEM = re.compile(r"^-\s+\[[^\]]+\]\([^)]+\)(?::\s*.*)?$")


def validate_llms_txt(text: str) -> list[str]:
    """Return concrete format errors for the documented llms.txt convention."""

    lines = text.lstrip("\ufeff").splitlines()
    nonblank = [(index, line.strip()) for index, line in enumerate(lines, start=1) if line.strip()]
    if not nonblank:
        return ["file is empty"]

    errors: list[str] = []
    first_number, first = nonblank[0]
    if not H1.match(first):
        errors.append(f"line {first_number} must be the required H1 site name")

    h1_lines = [number for number, line in nonblank if H1.match(line)]
    if len(h1_lines) > 1:
        errors.append(f"only one H1 is allowed; found H1 headings on lines {h1_lines}")

    current_section: tuple[int, str] | None = None
    section_links = 0
    for number, line in nonblank[1:]:
        if H2.match(line):
            if current_section and section_links == 0:
                errors.append(f"H2 section on line {current_section[0]} has no link-list items")
            current_section = (number, line)
            section_links = 0
            continue
        if ANY_HEADING.match(line):
            errors.append(f"line {number} uses an unsupported heading level")
            continue
        if current_section:
            if LINK_ITEM.match(line):
                section_links += 1
            else:
                errors.append(f"line {number} in an H2 section must be a markdown link-list item")

    if current_section and section_links == 0:
        errors.append(f"H2 section on line {current_section[0]} has no link-list items")
    return errors


@dataclass(frozen=True)
class ReadPage:
    url: str
    data: PageData


class GenerationError(RuntimeError):
    """A draft could not be produced without guessing."""


def generate_llms_txt(urls: list[str], timeout: float = 10.0) -> str:
    """Draft llms.txt from pages that were actually fetched and parsed."""

    if not urls:
        raise GenerationError("at least one page URL is required")

    pages: list[ReadPage] = []
    for url in urls:
        try:
            text = fetch_text(url, timeout=timeout)
        except FetchFailure as exc:
            raise GenerationError(f"could not read {url}: {exc}") from exc
        data = parse_html(text)
        if not data.saw_html:
            raise GenerationError(f"could not parse recognizable HTML from {url}")
        pages.append(ReadPage(url=url, data=data))

    first = pages[0]
    title = first.data.title or next(
        (text for level, text in first.data.headings if level == 1 and text),
        first.url,
    )
    lines = [f"# {title}", ""]
    if first.data.meta_description:
        lines.extend([f"> {first.data.meta_description}", ""])
    lines.extend(["## Pages", ""])

    for page in pages:
        label = page.data.title or next(
            (text for level, text in page.data.headings if level == 1 and text),
            page.url,
        )
        description = f": {page.data.meta_description}" if page.data.meta_description else ""
        lines.append(f"- [{label}]({page.url}){description}")

    return "\n".join(lines).rstrip() + "\n"
