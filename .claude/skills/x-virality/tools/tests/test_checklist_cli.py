"""Tests for the pre-publish checklist CLI walker."""
from __future__ import annotations

from pathlib import Path

import pytest

import checklist_cli as cc


SKILL_DIR = Path(__file__).resolve().parent.parent.parent
LIVE_CHECKLIST = SKILL_DIR / "checklist.md"


# ---------------------------------------------------------------------------
# parse_checklist
# ---------------------------------------------------------------------------


def test_parse_live_checklist_finds_items():
    items = cc.parse_checklist(LIVE_CHECKLIST)
    assert len(items) >= 10, "expected the real checklist to have many items"
    # Section names are populated.
    assert all(item.section for item in items)
    # Item text is populated.
    assert all(item.text for item in items)


def test_parse_assigns_correct_section(tmp_path: Path):
    md = tmp_path / "c.md"
    md.write_text(
        "# Title\n\n"
        "## First section\n\n"
        "- [ ] item A\n"
        "- [ ] item B\n"
        "\n## Second section\n\n"
        "- [ ] item C\n"
    )
    items = cc.parse_checklist(md)
    sections = [item.section for item in items]
    assert sections == ["First section", "First section", "Second section"]


def test_parse_ignores_already_checked(tmp_path: Path):
    md = tmp_path / "c.md"
    md.write_text(
        "## Section\n\n"
        "- [x] already done\n"
        "- [ ] still to do\n"
    )
    items = cc.parse_checklist(md)
    assert len(items) == 1
    assert items[0].text == "still to do"


def test_parse_handles_nested_indentation(tmp_path: Path):
    md = tmp_path / "c.md"
    md.write_text(
        "## Section\n\n"
        "  - [ ] indented item\n"
        "- [ ] top item\n"
    )
    items = cc.parse_checklist(md)
    texts = {i.text for i in items}
    assert texts == {"indented item", "top item"}


# ---------------------------------------------------------------------------
# walk + Verdict
# ---------------------------------------------------------------------------


def _items() -> list[cc.ChecklistItem]:
    return [
        cc.ChecklistItem(section="A", text="a1", line_no=1),
        cc.ChecklistItem(section="A", text="a2", line_no=2),
        cc.ChecklistItem(section="B", text="b1", line_no=3),
    ]


def test_walk_with_all_pass_returns_zero_fails():
    verdict = cc.walk(_items(), prompt=lambda _i: True)
    assert len(verdict.passes) == 3
    assert verdict.fails == []
    assert verdict.skips == []
    assert verdict.should_rewrite is False


def test_walk_with_one_fail_below_threshold_does_not_recommend_rewrite():
    answers = iter([True, False, True])
    verdict = cc.walk(_items(), prompt=lambda _i: next(answers))
    assert len(verdict.fails) == 1
    assert verdict.should_rewrite is False


def test_walk_with_two_fails_recommends_rewrite():
    answers = iter([False, False, True])
    verdict = cc.walk(_items(), prompt=lambda _i: next(answers))
    assert len(verdict.fails) == 2
    assert verdict.should_rewrite is True


def test_walk_with_skips_does_not_count_as_fail():
    verdict = cc.walk(_items(), prompt=lambda _i: None)
    assert len(verdict.skips) == 3
    assert verdict.fails == []
    assert verdict.should_rewrite is False


# ---------------------------------------------------------------------------
# summary / json
# ---------------------------------------------------------------------------


def test_summary_human_includes_verdict():
    verdict = cc.walk(_items(), prompt=lambda _i: True)
    text = verdict.summary()
    assert "SHIP IT" in text
    assert "Pass:  3" in text


def test_summary_failure_includes_fail_list():
    answers = iter([False, False, True])
    verdict = cc.walk(_items(), prompt=lambda _i: next(answers))
    text = verdict.summary()
    assert "REWRITE" in text
    assert "Failed items:" in text
    assert "a1" in text


def test_to_json_round_trips():
    import json
    verdict = cc.walk(_items(), prompt=lambda _i: True)
    data = json.loads(verdict.to_json())
    assert data["passes"] == 3
    assert data["fails"] == 0
    assert data["should_rewrite"] is False
    assert len(data["items"]) == 3


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_non_interactive_auto_pass_returns_zero(tmp_path: Path, capsys):
    md = tmp_path / "c.md"
    md.write_text(
        "## Section\n\n- [ ] one\n- [ ] two\n- [ ] three\n"
    )
    rc = cc.main(
        ["--non-interactive", "--auto-pass", "--checklist", str(md)]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "SHIP IT" in out


def test_main_non_interactive_default_skip_returns_zero(tmp_path: Path, capsys):
    md = tmp_path / "c.md"
    md.write_text("## Section\n\n- [ ] one\n")
    rc = cc.main(["--non-interactive", "--checklist", str(md)])
    assert rc == 0


def test_main_emits_json(tmp_path: Path, capsys):
    import json
    md = tmp_path / "c.md"
    md.write_text("## Section\n\n- [ ] one\n")
    rc = cc.main(
        ["--non-interactive", "--auto-pass",
         "--json", "--checklist", str(md)]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["passes"] == 1
