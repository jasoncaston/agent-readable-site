"""Console entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .linter import InspectionError, inspect_site
from .llms import GenerationError, generate_llms_txt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-readable-site",
        description="Inspect observable site metadata or draft llms.txt from pages you can read.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser("lint", help="Inspect one site page")
    lint_parser.add_argument("url", help="HTTP, HTTPS, or file URL to inspect")
    lint_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    lint_parser.add_argument("--timeout", type=float, default=10.0, help="Fetch timeout in seconds")

    generate_parser = subparsers.add_parser("generate", help="Draft llms.txt from fetched pages")
    generate_parser.add_argument("urls", nargs="+", help="Page URLs to read and include")
    generate_parser.add_argument("--output", type=Path, help="Write the draft to this file instead of stdout")
    generate_parser.add_argument("--timeout", type=float, default=10.0, help="Fetch timeout in seconds")
    return parser


def render_report(report) -> str:
    lines = [
        "Agent-readable site report",
        f"URL: {report.url}",
        f"Score: {report.score}/{report.maximum_score}",
        f"Schema types: {', '.join(report.schema_types) if report.schema_types else 'none'}",
        "",
        "Defects:",
    ]
    if report.defects:
        lines.extend(f"- {defect.code}: {defect.message}" for defect in report.defects)
    else:
        lines.append("- none")

    lines.extend(["", "Crawler access facts:"])
    if report.crawler_access:
        lines.extend(
            f"- {agent}: {details['status']}"
            for agent, details in report.crawler_access.items()
        )
    else:
        lines.append("- unavailable")
    if report.facts:
        lines.extend(["", "Notes:"])
        lines.extend(f"- {fact}" for fact in report.facts)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "lint":
        try:
            report = inspect_site(args.url, timeout=args.timeout)
        except InspectionError as exc:
            if args.json:
                print(json.dumps({"url": args.url, "error": str(exc)}, indent=2, sort_keys=True))
            else:
                print(f"Inspection failed: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(render_report(report))
        return 1 if report.defects else 0

    try:
        draft = generate_llms_txt(args.urls, timeout=args.timeout)
    except GenerationError as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(draft, encoding="utf-8")
        print(f"Draft written to {args.output}")
    else:
        print(draft, end="")
    return 0
