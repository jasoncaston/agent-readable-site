from agent_readable_site.robots import crawler_access_facts


def test_explicit_ai_crawler_block_is_reported_as_fact() -> None:
    robots = """User-agent: *
Allow: /

User-agent: GPTBot
Disallow: /
"""

    facts = crawler_access_facts(robots)

    assert facts["GPTBot"]["status"] == "blocked"
    assert facts["GPTBot"]["disallow"] == ["/"]
    assert facts["OAI-AdsBot"]["status"] == "allowed"
    assert facts["OAI-SearchBot"]["status"] == "allowed"
