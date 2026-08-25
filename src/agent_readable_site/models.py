"""Data models shared by the linter and command line interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Defect:
    """One observable conformance gap."""

    code: str
    message: str


@dataclass(frozen=True)
class ScoreItem:
    """One documented scoring criterion."""

    awarded: int
    maximum: int
    reason: str


@dataclass
class SiteReport:
    """Complete linter result for one readable page."""

    url: str
    score: int
    maximum_score: int
    defects: list[Defect] = field(default_factory=list)
    schema_types: list[str] = field(default_factory=list)
    crawler_access: dict[str, dict[str, Any]] = field(default_factory=dict)
    facts: list[str] = field(default_factory=list)
    scoring: dict[str, ScoreItem] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
