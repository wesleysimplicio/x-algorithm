#!/usr/bin/env python3
"""Interactive walker for the x-virality pre-publish checklist.

Parses `.claude/skills/x-virality/checklist.md`, walks the user through each
checklist item, and prints a structured summary of which items passed,
failed, or were skipped.

Usage:
    python .claude/skills/x-virality/tools/checklist_cli.py
    python .claude/skills/x-virality/tools/checklist_cli.py --non-interactive --auto-pass
    python .claude/skills/x-virality/tools/checklist_cli.py --json

The CLI is also importable as a library:

    from checklist_cli import parse_checklist, ChecklistItem
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

CHECKLIST_PATH = (
    Path(__file__).resolve().parent.parent / "checklist.md"
)
CHECKBOX_RE = re.compile(r"^\s*-\s*\[\s*\]\s*(.+?)\s*$")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
THRESHOLD_FAIL_REWRITE = 2


@dataclass
class ChecklistItem:
    """One unchecked item from the checklist."""

    section: str
    text: str
    line_no: int


@dataclass
class ItemResult:
    """User's answer for a single checklist item."""

    item: ChecklistItem
    passed: bool | None  # True/False/None (skipped)

    def to_dict(self) -> dict:
        return {
            "section": self.item.section,
            "text": self.item.text,
            "line_no": self.item.line_no,
            "passed": self.passed,
        }


@dataclass
class Verdict:
    """Aggregate result of a walk."""

    results: list[ItemResult] = field(default_factory=list)

    @property
    def fails(self) -> list[ItemResult]:
        return [r for r in self.results if r.passed is False]

    @property
    def passes(self) -> list[ItemResult]:
        return [r for r in self.results if r.passed is True]

    @property
    def skips(self) -> list[ItemResult]:
        return [r for r in self.results if r.passed is None]

    @property
    def should_rewrite(self) -> bool:
        """The checklist says: if 2+ items fail, rewrite before posting."""
        return len(self.fails) >= THRESHOLD_FAIL_REWRITE

    def summary(self) -> str:
        lines = [
            f"Checklist walked: {len(self.results)} items",
            f"  Pass:  {len(self.passes)}",
            f"  Fail:  {len(self.fails)}",
            f"  Skip:  {len(self.skips)}",
        ]
        if self.should_rewrite:
            lines.append("")
            lines.append(
                f"VERDICT: REWRITE — {len(self.fails)} failures "
                f"(threshold: {THRESHOLD_FAIL_REWRITE})."
            )
        elif self.fails:
            lines.append("")
            lines.append(
                f"VERDICT: SHIP WITH CAUTION — {len(self.fails)} "
                "failure(s), below rewrite threshold."
            )
        else:
            lines.append("")
            lines.append("VERDICT: SHIP IT — all items pass or skipped.")
        if self.fails:
            lines.append("")
            lines.append("Failed items:")
            for r in self.fails:
                lines.append(f"  [{r.item.section}] {r.item.text}")
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {
                "items": [r.to_dict() for r in self.results],
                "passes": len(self.passes),
                "fails": len(self.fails),
                "skips": len(self.skips),
                "should_rewrite": self.should_rewrite,
            },
            indent=2,
        )


def parse_checklist(checklist_path: Path = CHECKLIST_PATH) -> list[ChecklistItem]:
    """Read the checklist markdown and extract every `- [ ]` item."""
    items: list[ChecklistItem] = []
    current_section = "(no section)"
    text = checklist_path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        section_match = SECTION_RE.match(line)
        if section_match:
            current_section = section_match.group(1)
            continue
        checkbox_match = CHECKBOX_RE.match(line)
        if checkbox_match:
            items.append(
                ChecklistItem(
                    section=current_section,
                    text=checkbox_match.group(1),
                    line_no=line_no,
                )
            )
    return items


def _interactive_prompt(item: ChecklistItem) -> bool | None:
    """Default prompt: ask the user pass/fail/skip for one item."""
    while True:
        sys.stdout.write(
            f"\n[{item.section}]\n  {item.text}\n  pass/fail/skip [p/f/s] > "
        )
        sys.stdout.flush()
        answer = sys.stdin.readline().strip().lower()
        if answer in {"p", "pass", "y", "yes"}:
            return True
        if answer in {"f", "fail", "n", "no"}:
            return False
        if answer in {"s", "skip", ""}:
            return None
        print(f"  unrecognized answer {answer!r}; try p/f/s")


def walk(
    items: Iterable[ChecklistItem],
    prompt: Callable[[ChecklistItem], bool | None] = _interactive_prompt,
) -> Verdict:
    """Walk every item via the given prompt function and return a Verdict."""
    verdict = Verdict()
    for item in items:
        answer = prompt(item)
        verdict.results.append(ItemResult(item=item, passed=answer))
    return verdict


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Walk the x-virality pre-publish checklist."
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Don't prompt — every item is auto-answered.",
    )
    parser.add_argument(
        "--auto-pass",
        action="store_true",
        help="With --non-interactive, auto-pass every item (for CI smoke).",
    )
    parser.add_argument(
        "--json", dest="emit_json", action="store_true",
        help="Emit a JSON report instead of a human summary.",
    )
    parser.add_argument(
        "--checklist", type=Path, default=CHECKLIST_PATH,
        help="Path to checklist.md (default: skill's checklist.md).",
    )
    args = parser.parse_args(argv)

    items = parse_checklist(args.checklist)

    if args.non_interactive:
        decision = True if args.auto_pass else None
        prompt = lambda _item: decision  # noqa: E731
    else:
        prompt = _interactive_prompt

    verdict = walk(items, prompt=prompt)

    if args.emit_json:
        print(verdict.to_json())
    else:
        print(verdict.summary())

    return 1 if verdict.should_rewrite else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
