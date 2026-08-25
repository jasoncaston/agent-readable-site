"""robots.txt parsing for factual AI user-agent reporting."""

from __future__ import annotations

from dataclasses import dataclass, field


KNOWN_AI_USER_AGENTS = (
    "OAI-SearchBot",
    "GPTBot",
    "ChatGPT-User",
    "Claude-SearchBot",
    "ClaudeBot",
    "Claude-User",
    "Google-Extended",
    "PerplexityBot",
    "Perplexity-User",
)


@dataclass
class RobotGroup:
    agents: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    disallow: list[str] = field(default_factory=list)


def parse_robots(text: str) -> list[RobotGroup]:
    groups: list[RobotGroup] = []
    current = RobotGroup()
    has_rules = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if has_rules:
                groups.append(current)
                current = RobotGroup()
                has_rules = False
            current.agents.append(value.lower())
        elif field in {"allow", "disallow"} and current.agents:
            getattr(current, field).append(value)
            has_rules = True

    if current.agents:
        groups.append(current)
    return groups


def crawler_access_facts(text: str) -> dict[str, dict[str, object]]:
    groups = parse_robots(text)
    results: dict[str, dict[str, object]] = {}
    for agent in KNOWN_AI_USER_AGENTS:
        exact = [group for group in groups if agent.lower() in group.agents]
        applicable = exact or [group for group in groups if "*" in group.agents]
        disallow = sorted({rule for group in applicable for rule in group.disallow if rule})
        allow = sorted({rule for group in applicable for rule in group.allow if rule})
        blocked = "/" in disallow and "/" not in allow
        partial = bool(disallow) and not blocked
        status = "blocked" if blocked else "partially restricted" if partial else "allowed"
        results[agent] = {
            "status": status,
            "disallow": disallow,
            "allow": allow,
        }
    return results
