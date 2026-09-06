"""
Generate a local HTML preview of the parking digest using mock scenario data.

Usage:
    python3 scripts/preview.py                     # default: 'mixed' scenario
    python3 scripts/preview.py --scenario high-noon-game
    python3 scripts/preview.py --list              # list available scenarios
    python3 scripts/preview.py --all               # generate all scenarios

Output is written to docs/preview.html (or docs/preview-<scenario>.html for --all).
Open with:  python3 -m http.server 8080 --directory docs/
Then visit: http://localhost:8080/preview.html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running as a script
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from src.output.html import format_html
from src.scoring.impact import score_events
from tests.factories import BASE_DATE, SCENARIOS


def _write(path: Path, html: str, scenario_name: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"[{scenario_name}] {description}")
    print(f"  -> {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML preview from mock scenario")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--scenario", "-s",
        default="mixed",
        choices=list(SCENARIOS),
        metavar="SCENARIO",
        help="Scenario name (default: mixed)",
    )
    group.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available scenarios and exit",
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generate all scenarios to docs/preview-<name>.html",
    )
    args = parser.parse_args()

    if args.list:
        print("Available scenarios:\n")
        for name, (description, events) in SCENARIOS.items():
            print(f"  {name:<28}  {description}")
        return

    docs = _ROOT / "docs"

    if args.all:
        for name, (description, events) in SCENARIOS.items():
            scored = score_events(events)
            html = format_html(scored, report_date=BASE_DATE)
            _write(docs / f"preview-{name}.html", html, name, description)
        print(f"\nServe with:  python3 -m http.server 8080 --directory {docs}")
        print("Then open:   http://localhost:8080/preview-mixed.html")
        return

    name = args.scenario
    description, events = SCENARIOS[name]
    scored = score_events(events)
    html = format_html(scored, report_date=BASE_DATE)
    out = docs / "preview.html"
    _write(out, html, name, description)
    print(f"\nServe with:  python3 -m http.server 8080 --directory {docs}")
    print("Then open:   http://localhost:8080/preview.html")


if __name__ == "__main__":
    main()
