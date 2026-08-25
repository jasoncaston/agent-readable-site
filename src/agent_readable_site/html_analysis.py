"""Small HTML and JSON-LD parsers built on the Python standard library."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any


WHITESPACE = re.compile(r"\s+")
RECOGNIZED_HTML_ELEMENTS = frozenset(
    {
        "a",
        "abbr",
        "address",
        "area",
        "article",
        "aside",
        "audio",
        "b",
        "base",
        "bdi",
        "bdo",
        "blockquote",
        "body",
        "br",
        "button",
        "canvas",
        "caption",
        "cite",
        "code",
        "col",
        "colgroup",
        "data",
        "datalist",
        "dd",
        "del",
        "details",
        "dfn",
        "dialog",
        "div",
        "dl",
        "dt",
        "em",
        "embed",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hgroup",
        "hr",
        "html",
        "i",
        "iframe",
        "img",
        "input",
        "ins",
        "kbd",
        "label",
        "legend",
        "li",
        "link",
        "main",
        "map",
        "mark",
        "menu",
        "meta",
        "meter",
        "nav",
        "noscript",
        "object",
        "ol",
        "optgroup",
        "option",
        "output",
        "p",
        "picture",
        "pre",
        "progress",
        "q",
        "rp",
        "rt",
        "ruby",
        "s",
        "samp",
        "script",
        "search",
        "section",
        "select",
        "slot",
        "small",
        "source",
        "span",
        "strong",
        "style",
        "sub",
        "summary",
        "sup",
        "svg",
        "table",
        "tbody",
        "td",
        "template",
        "textarea",
        "tfoot",
        "th",
        "thead",
        "time",
        "title",
        "tr",
        "track",
        "u",
        "ul",
        "var",
        "video",
        "wbr",
    }
)


def clean_text(value: str) -> str:
    return WHITESPACE.sub(" ", value).strip()


@dataclass
class PageData:
    title: str = ""
    meta_description: str = ""
    canonical_url: str = ""
    headings: list[tuple[int, str]] = field(default_factory=list)
    body_text: str = ""
    main_text: str = ""
    image_alt_texts: list[str] = field(default_factory=list)
    json_ld_blocks: list[str] = field(default_factory=list)
    saw_html: bool = False
    saw_main: bool = False


class PageParser(HTMLParser):
    """Collect only the fields needed by the linter."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data = PageData()
        self._title_depth = 0
        self._title_parts: list[str] = []
        self._excluded_depth = 0
        self._main_depth = 0
        self._body_parts: list[str] = []
        self._main_parts: list[str] = []
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): (value or "") for key, value in attrs}
        if tag in RECOGNIZED_HTML_ELEMENTS:
            self.data.saw_html = True
        if tag == "title":
            self._title_depth += 1
        if tag == "main":
            self.data.saw_main = True
            self._main_depth += 1
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"}:
            self._excluded_depth += 1
        if tag == "script" and attr.get("type", "").lower().split(";")[0].strip() == "application/ld+json":
            self._json_ld_parts = []
        if tag == "meta" and attr.get("name", "").lower() == "description":
            self.data.meta_description = clean_text(attr.get("content", ""))
        if tag == "link":
            rel_tokens = {token.lower() for token in attr.get("rel", "").split()}
            if "canonical" in rel_tokens:
                self.data.canonical_url = attr.get("href", "").strip()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_level = int(tag[1])
            self._heading_parts = []
        if tag == "img":
            alt = clean_text(attr.get("alt", ""))
            if alt:
                self.data.image_alt_texts.append(alt)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag == "script" and self._json_ld_parts is not None:
            self.data.json_ld_blocks.append("".join(self._json_ld_parts).strip())
            self._json_ld_parts = None
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"} and self._excluded_depth:
            self._excluded_depth -= 1
        if self._heading_level is not None and tag == f"h{self._heading_level}":
            self.data.headings.append((self._heading_level, clean_text(" ".join(self._heading_parts))))
            self._heading_level = None
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)
        if self._title_depth:
            self._title_parts.append(data)
        if self._heading_level is not None:
            self._heading_parts.append(data)
        if self._excluded_depth == 0:
            value = clean_text(data)
            if value:
                self._body_parts.append(value)
                if self._main_depth:
                    self._main_parts.append(value)

    def close(self) -> None:
        super().close()
        self.data.title = clean_text(" ".join(self._title_parts))
        self.data.body_text = clean_text(" ".join(self._body_parts))
        self.data.main_text = clean_text(" ".join(self._main_parts))


def parse_html(text: str) -> PageData:
    parser = PageParser()
    parser.feed(text)
    parser.close()
    return parser.data


def parse_json_ld(blocks: list[str]) -> tuple[list[Any], list[str], list[str]]:
    """Parse JSON-LD blocks and return documents, declared types, and errors."""

    documents: list[Any] = []
    errors: list[str] = []
    for index, block in enumerate(blocks, start=1):
        if not block:
            errors.append(f"block {index} is empty")
            continue
        try:
            documents.append(json.loads(block))
        except json.JSONDecodeError as exc:
            errors.append(f"block {index} is malformed at line {exc.lineno}, column {exc.colno}: {exc.msg}")

    types: set[str] = set()
    for node in iter_json_ld_nodes(documents):
        declared = node.get("@type")
        if isinstance(declared, str):
            types.add(declared)
        elif isinstance(declared, list):
            types.update(item for item in declared if isinstance(item, str))
    return documents, sorted(types), errors


def iter_json_ld_nodes(values: Any):
    """Yield dictionary nodes from arrays and @graph containers."""

    if isinstance(values, list):
        for value in values:
            yield from iter_json_ld_nodes(value)
    elif isinstance(values, dict):
        yield values
        graph = values.get("@graph")
        if graph is not None:
            yield from iter_json_ld_nodes(graph)
