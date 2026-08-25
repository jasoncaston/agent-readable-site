from pathlib import Path

from agent_readable_site.llms import generate_llms_txt, validate_llms_txt


FIXTURES = Path(__file__).parent / "fixtures"


def test_documented_llms_shape_is_valid() -> None:
    text = (FIXTURES / "clean" / "llms.txt").read_text(encoding="utf-8")

    assert validate_llms_txt(text) == []


def test_llms_requires_h1_before_link_sections() -> None:
    errors = validate_llms_txt("## Pages\n\n- [Home](https://example.com)\n")

    assert "line 1 must be the required H1 site name" in errors


def test_generator_uses_only_fetched_page_metadata() -> None:
    url = (FIXTURES / "clean" / "index.html").resolve().as_uri()

    draft = generate_llms_txt([url])

    assert draft.startswith("# Northstar Lantern Works | Fictional lighting plans\n")
    assert "Northstar Lantern Works publishes fictional lantern plans" in draft
    assert f"[{ 'Northstar Lantern Works | Fictional lighting plans' }]({url})" in draft
