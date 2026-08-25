import json
from pathlib import Path

import pytest

from agent_readable_site.linter import InspectionError, inspect_site
from agent_readable_site.cli import main


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_url(name: str) -> str:
    return (FIXTURES / name / "index.html").resolve().as_uri()


def defect_messages(report) -> list[str]:
    return [defect.message for defect in report.defects]


def test_clean_site_reports_parsed_values() -> None:
    report = inspect_site(fixture_url("clean"))

    assert report.score == 100
    assert report.maximum_score == 100
    assert report.defects == []
    assert report.schema_types == ["Organization"]
    assert report.crawler_access["GPTBot"]["status"] == "allowed"
    assert report.scoring["visible_claims"].awarded == 15


def test_valid_html5_without_html_tag_is_inspected() -> None:
    report = inspect_site(fixture_url("optional_tags"))

    assert report.score == 100
    assert report.defects == []
    assert report.schema_types == ["Organization"]
    assert report.scoring["headings"].awarded == 10
    assert report.scoring["visible_claims"].awarded == 15


def test_text_without_recognized_html_fails_loud(tmp_path) -> None:
    page = tmp_path / "index.html"
    page.write_text("This is text, but it is not recognizable HTML.", encoding="utf-8")

    with pytest.raises(InspectionError) as caught:
        inspect_site(page.as_uri())

    assert str(caught.value) == f"could not parse recognizable HTML, so no score was produced: {page.as_uri()}"


def test_missing_llms_txt_names_the_specific_gap() -> None:
    report = inspect_site(fixture_url("missing_llms"))

    assert report.score == 80
    assert "llms.txt is missing at the site root" in defect_messages(report)
    assert report.scoring["llms_txt"].awarded == 0
    assert report.schema_types == ["Organization"]


def test_missing_json_ld_reports_both_structured_data_gaps() -> None:
    report = inspect_site(fixture_url("no_jsonld"))

    assert report.score == 70
    assert report.schema_types == []
    assert "JSON-LD is missing" in defect_messages(report)
    assert "Organization or Person schema is missing" in defect_messages(report)


def test_malformed_json_ld_reports_parse_location() -> None:
    report = inspect_site(fixture_url("malformed_jsonld"))

    assert report.score == 70
    assert report.schema_types == []
    assert any(
        message.startswith("JSON-LD block 1 is malformed at line 1, column")
        for message in defect_messages(report)
    )
    assert report.scoring["json_ld"].reason == "At least one JSON-LD block could not be parsed"


def test_unfetchable_url_produces_no_score() -> None:
    missing = (FIXTURES / "does-not-exist" / "index.html").resolve().as_uri()

    with pytest.raises(InspectionError) as caught:
        inspect_site(missing)

    assert "could not fetch the page, so no score was produced" in str(caught.value)
    assert "resource not found" in str(caught.value)


def test_primary_claim_in_image_is_named() -> None:
    report = inspect_site(fixture_url("image_claim"))

    assert report.score == 85
    assert report.schema_types == ["Organization"]
    assert (
        "Primary claim appears to be trapped in an image; visible page text is below the substantive threshold"
        in defect_messages(report)
    )
    assert report.scoring["visible_claims"].awarded == 0


def test_json_cli_contains_parsed_values(capsys) -> None:
    result = main(["lint", fixture_url("clean"), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["score"] == 100
    assert payload["schema_types"] == ["Organization"]
    assert payload["defects"] == []
