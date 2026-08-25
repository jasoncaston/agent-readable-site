import json
from pathlib import Path


TEMPLATES = Path(__file__).parents[1] / "templates"


def test_all_required_templates_are_valid_fictional_json_ld() -> None:
    expected = {"Organization", "Person", "Service", "Course", "Article", "FAQPage"}
    found = set()

    for path in sorted(TEMPLATES.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        found.add(document["@type"])
        rendered = json.dumps(document)
        assert "northstar-lantern.example" in rendered or document["@type"] == "FAQPage"

    assert found == expected
