"""Site inspection and evidence-limited scoring."""

from __future__ import annotations

from typing import Any

from .fetch import FetchFailure, ResourceMissing, fetch_text, root_resource_url
from .html_analysis import PageData, iter_json_ld_nodes, parse_html, parse_json_ld
from .llms import validate_llms_txt
from .models import Defect, ScoreItem, SiteReport
from .robots import crawler_access_facts


SCORING_WEIGHTS = {
    "llms_txt": 20,
    "json_ld": 15,
    "entity_schema": 15,
    "visible_claims": 15,
    "headings": 10,
    "title": 10,
    "meta_description": 10,
    "canonical": 5,
}

GENERIC_HEADINGS = {
    "home",
    "welcome",
    "hello",
    "learn more",
    "discover",
    "explore",
    "about",
    "services",
}


class InspectionError(RuntimeError):
    """Inspection could not produce a trustworthy score."""


def _score(scoring: dict[str, ScoreItem]) -> int:
    return sum(item.awarded for item in scoring.values())


def _substantive(value: str, minimum_characters: int, minimum_words: int) -> bool:
    words = [word for word in value.split() if any(character.isalpha() for character in word)]
    return len(value.strip()) >= minimum_characters and len(words) >= minimum_words


def _heading_defects(page: PageData) -> list[str]:
    defects: list[str] = []
    levels = [level for level, _ in page.headings]
    h1_count = levels.count(1)
    if h1_count == 0:
        defects.append("Heading structure has no h1")
    elif h1_count > 1:
        defects.append("Heading structure has multiple h1 elements")

    previous = 0
    for level in levels:
        if previous and level > previous + 1:
            defects.append(f"Heading structure skips from h{previous} to h{level}")
            break
        previous = level

    primary = [text for level, text in page.headings if level in {1, 2}]
    descriptive = any(
        _substantive(text, 12, 2) and text.casefold() not in GENERIC_HEADINGS
        for text in primary
    )
    if not descriptive:
        defects.append("H1 and H2 headings appear decorative rather than descriptive")
    return defects


def _entity_schema_status(documents: list[Any]) -> tuple[bool, str]:
    candidates: list[dict[str, Any]] = []
    for node in iter_json_ld_nodes(documents):
        declared = node.get("@type")
        types = {declared} if isinstance(declared, str) else set(declared or [])
        if {"Organization", "Person"} & types:
            candidates.append(node)

    if not candidates:
        return False, "Organization or Person schema is missing"
    for candidate in candidates:
        missing = [field for field in ("name", "url", "description") if not candidate.get(field)]
        if not missing:
            return True, "Organization or Person schema has name, url, and description"
    missing_sets = [
        ", ".join(field for field in ("name", "url", "description") if not candidate.get(field))
        for candidate in candidates
    ]
    return False, f"Organization or Person schema is incomplete; missing: {'; '.join(missing_sets)}"


def inspect_site(url: str, timeout: float = 10.0) -> SiteReport:
    """Fetch and inspect one page plus its root metadata resources."""

    try:
        page_text = fetch_text(url, timeout=timeout)
    except FetchFailure as exc:
        raise InspectionError(f"could not fetch the page, so no score was produced: {exc}") from exc

    try:
        page = parse_html(page_text)
    except Exception as exc:
        raise InspectionError(f"could not parse the page, so no score was produced: {url}: {exc}") from exc
    if not page.saw_html:
        raise InspectionError(f"could not parse recognizable HTML, so no score was produced: {url}")

    defects: list[Defect] = []
    facts: list[str] = []
    scoring: dict[str, ScoreItem] = {}

    llms_url = root_resource_url(url, "llms.txt")
    try:
        llms_text = fetch_text(llms_url, timeout=timeout)
    except ResourceMissing:
        defects.append(Defect("llms-missing", "llms.txt is missing at the site root"))
        scoring["llms_txt"] = ScoreItem(0, 20, "The root llms.txt file is absent")
    except FetchFailure as exc:
        raise InspectionError(f"could not inspect llms.txt, so no score was produced: {exc}") from exc
    else:
        llms_errors = validate_llms_txt(llms_text)
        if llms_errors:
            for error in llms_errors:
                defects.append(Defect("llms-malformed", f"llms.txt is not well-formed: {error}"))
            scoring["llms_txt"] = ScoreItem(8, 20, "llms.txt exists but does not conform")
        else:
            scoring["llms_txt"] = ScoreItem(20, 20, "llms.txt exists and conforms")

    documents, schema_types, json_errors = parse_json_ld(page.json_ld_blocks)
    if not page.json_ld_blocks:
        defects.append(Defect("jsonld-missing", "JSON-LD is missing"))
        scoring["json_ld"] = ScoreItem(0, 15, "No JSON-LD block was declared")
    elif json_errors:
        for error in json_errors:
            defects.append(Defect("jsonld-malformed", f"JSON-LD {error}"))
        scoring["json_ld"] = ScoreItem(0, 15, "At least one JSON-LD block could not be parsed")
    else:
        scoring["json_ld"] = ScoreItem(15, 15, "JSON-LD is present and parseable")

    entity_ok, entity_reason = _entity_schema_status(documents)
    if entity_ok:
        scoring["entity_schema"] = ScoreItem(15, 15, entity_reason)
    else:
        defects.append(Defect("entity-schema", entity_reason))
        scoring["entity_schema"] = ScoreItem(0, 15, entity_reason)

    visible_text = page.main_text if page.saw_main else page.body_text
    if _substantive(visible_text, 100, 15):
        scoring["visible_claims"] = ScoreItem(15, 15, "Substantive primary claims are present as visible text")
    else:
        image_claim = any(_substantive(alt, 50, 8) for alt in page.image_alt_texts)
        if image_claim:
            message = "Primary claim appears to be trapped in an image; visible page text is below the substantive threshold"
            code = "primary-claim-image-only"
        else:
            message = "Primary claims are not present as substantive visible text"
            code = "primary-claim-thin"
        defects.append(Defect(code, message))
        scoring["visible_claims"] = ScoreItem(0, 15, message)

    heading_defects = _heading_defects(page)
    if heading_defects:
        defects.extend(Defect("heading-structure", message) for message in heading_defects)
        scoring["headings"] = ScoreItem(0, 10, "; ".join(heading_defects))
    else:
        scoring["headings"] = ScoreItem(10, 10, "H1 and H2 structure is descriptive and ordered")

    if _substantive(page.title, 12, 2) and page.title.casefold() not in GENERIC_HEADINGS:
        scoring["title"] = ScoreItem(10, 10, "The title is present and substantive")
    else:
        defects.append(Defect("title-thin", "Title is missing or not substantive"))
        scoring["title"] = ScoreItem(0, 10, "The title is missing or below the substantive threshold")

    if _substantive(page.meta_description, 50, 8):
        scoring["meta_description"] = ScoreItem(10, 10, "The meta description is present and substantive")
    else:
        defects.append(Defect("meta-description-thin", "Meta description is missing or not substantive"))
        scoring["meta_description"] = ScoreItem(0, 10, "The meta description is missing or below the substantive threshold")

    if page.canonical_url:
        scoring["canonical"] = ScoreItem(5, 5, "A canonical URL is declared")
    else:
        defects.append(Defect("canonical-missing", "Canonical URL is missing"))
        scoring["canonical"] = ScoreItem(0, 5, "No canonical URL was declared")

    robots_url = root_resource_url(url, "robots.txt")
    try:
        robots_text = fetch_text(robots_url, timeout=timeout)
    except ResourceMissing:
        crawler_access: dict[str, dict[str, object]] = {}
        facts.append("robots.txt is not present; no crawler blocking fact can be reported")
    except FetchFailure as exc:
        raise InspectionError(f"could not inspect robots.txt, so no score was produced: {exc}") from exc
    else:
        crawler_access = crawler_access_facts(robots_text)
        facts.append("Crawler access is reported as a robots.txt fact and does not affect the score")

    return SiteReport(
        url=url,
        score=_score(scoring),
        maximum_score=sum(SCORING_WEIGHTS.values()),
        defects=defects,
        schema_types=schema_types,
        crawler_access=crawler_access,
        facts=facts,
        scoring=scoring,
    )
