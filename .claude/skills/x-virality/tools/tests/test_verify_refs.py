"""Tests for the skill-references verifier."""
from __future__ import annotations

from pathlib import Path

import pytest

import verify_refs


SKILL_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Live regression: every cited path in the real skill exists.
# ---------------------------------------------------------------------------


def test_live_skill_references_all_resolve():
    checked, failures = verify_refs.verify(SKILL_DIR)
    assert checked > 0, "expected to find at least one source reference"
    if failures:
        msg = "\n".join(
            f"  {r.skill_file.name}:{r.line_no} -> `{r.cited_path}` ({reason})"
            for r, reason in failures
        )
        pytest.fail(f"broken refs:\n{msg}")


# ---------------------------------------------------------------------------
# Reference extraction unit tests.
# ---------------------------------------------------------------------------


def test_extract_references_picks_up_rust_paths(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("See `home-mixer/scorers/weighted_scorer.rs` for details.\n")
    refs = verify_refs.extract_references(md)
    assert len(refs) == 1
    assert refs[0].cited_path == "home-mixer/scorers/weighted_scorer.rs"
    assert refs[0].line_no == 1


def test_extract_references_strips_symbol_suffix(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("`home-mixer/scorers/ranking_scorer.rs::compute_weighted_score`\n")
    refs = verify_refs.extract_references(md)
    assert len(refs) == 1
    assert refs[0].cited_path == "home-mixer/scorers/ranking_scorer.rs"


def test_extract_references_picks_up_directories(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("Located in `home-mixer/filters/`.\n")
    refs = verify_refs.extract_references(md)
    assert len(refs) == 1
    assert refs[0].cited_path == "home-mixer/filters"


def test_extract_references_picks_up_python_paths(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("`grox/plans/plan_initial_banger.py` runs the banger screen.\n")
    refs = verify_refs.extract_references(md)
    assert len(refs) == 1
    assert refs[0].cited_path == "grox/plans/plan_initial_banger.py"


def test_extract_references_ignores_module_paths(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("`crate::params` is a Rust module, not a file.\n")
    refs = verify_refs.extract_references(md)
    assert refs == []


def test_extract_references_finds_multiple_per_file(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text(
        "First: `phoenix/grok.py`.\n"
        "Then `home-mixer/scorers/oon_scorer.rs` and `thunder/main.rs`.\n"
    )
    refs = verify_refs.extract_references(md)
    paths = {r.cited_path for r in refs}
    assert paths == {
        "phoenix/grok.py",
        "home-mixer/scorers/oon_scorer.rs",
        "thunder/main.rs",
    }


# ---------------------------------------------------------------------------
# verify() returns failures for nonexistent paths.
# ---------------------------------------------------------------------------


def test_verify_reports_missing_path(tmp_path: Path):
    # Build a tiny fake repo with a .git marker so repo_root resolves.
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "fake"
    skill_dir.mkdir(parents=True)
    md = skill_dir / "doc.md"
    md.write_text(
        "Exists: `real_file.rs`\n"
        "Missing: `path/does/not/exist.rs`\n"
    )
    (tmp_path / "real_file.rs").write_text("// real")

    checked, failures = verify_refs.verify(skill_dir)
    assert checked == 2
    assert len(failures) == 1
    assert failures[0][0].cited_path == "path/does/not/exist.rs"


def test_verify_reports_nothing_when_all_paths_exist(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "fake"
    skill_dir.mkdir(parents=True)
    md = skill_dir / "doc.md"
    md.write_text("Exists: `a.rs`. Also exists: `b/c.py`.\n")
    (tmp_path / "a.rs").write_text("//")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "c.py").write_text("#")

    checked, failures = verify_refs.verify(skill_dir)
    assert checked == 2
    assert failures == []


def test_main_returns_zero_on_clean_skill_directory(tmp_path: Path, capsys):
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "fake"
    skill_dir.mkdir(parents=True)
    md = skill_dir / "doc.md"
    md.write_text("Real: `existing.rs`\n")
    (tmp_path / "existing.rs").write_text("//")

    rc = verify_refs.main([str(skill_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_main_returns_one_on_broken_reference(tmp_path: Path, capsys):
    (tmp_path / ".git").mkdir()
    skill_dir = tmp_path / ".claude" / "skills" / "fake"
    skill_dir.mkdir(parents=True)
    md = skill_dir / "doc.md"
    md.write_text("Missing: `nope.rs`\n")

    rc = verify_refs.main([str(skill_dir)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "broken reference" in out
    assert "nope.rs" in out
