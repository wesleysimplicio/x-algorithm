#!/usr/bin/env python3
"""Verify every source path cited in the x-virality skill still exists.

The skill is source-grounded: every claim points to a file in this repo.
When the algorithm code moves or files are renamed, the skill must follow.
This script scans every markdown file under .claude/skills/x-virality/,
extracts cited paths, and asserts each one exists relative to repo root.

Exit code 0 on success, 1 on any missing reference (CI-friendly).

Run:
    python .claude/skills/x-virality/tools/verify_refs.py
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Paths inside backticks that look like source references we want to verify.
# We accept paths ending in .rs, .py, .md, .toml, .json, .npz, plus directories
# that end with a trailing slash. Symbol suffixes after `::` are stripped.
SOURCE_PATH_RE = re.compile(
    r"`([A-Za-z0-9_./-]+?(?:\.(?:rs|py|md|toml|json|npz|lock))|"
    r"[A-Za-z0-9_./-]+?/)(?:::[A-Za-z0-9_]+)?`"
)

# Paths we deliberately ignore: filenames mentioned generically or virtual
# paths that look like file references but aren't real files in this repo.
IGNORE_TOKENS = {
    "crate::params",        # Rust module path, not a file
    "params.rs",            # mentioned by name but not a real standalone file
    "params",
    "AGENTS.md",            # documented suggestion for Codex install, not a file in this repo
    "tota.skill.json",      # hypothetical Tota schema, not a real file
    "make verify-skill-refs",  # not a path
}

# Skill files we skip entirely. ROADMAP.md is the planning document and
# deliberately references files that don't exist yet (Sprint 2-6 deliverables).
SKIP_FILES = {"ROADMAP.md"}


@dataclass(frozen=True)
class Reference:
    """A single cited path inside a skill markdown file."""

    skill_file: Path
    cited_path: str
    line_no: int


def extract_references(skill_file: Path) -> list[Reference]:
    """Return every cited path inside ``skill_file`` worth verifying."""
    refs: list[Reference] = []
    text = skill_file.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in SOURCE_PATH_RE.finditer(line):
            cited = match.group(1)
            if cited in IGNORE_TOKENS:
                continue
            # Strip a single trailing slash for directory references.
            normalised = cited.rstrip("/")
            if not normalised:
                continue
            refs.append(
                Reference(
                    skill_file=skill_file,
                    cited_path=normalised,
                    line_no=line_no,
                )
            )
    return refs


def find_skill_markdown(skill_dir: Path) -> list[Path]:
    """Every markdown file inside the skill folder, recursively, except SKIP_FILES."""
    return sorted(
        p for p in skill_dir.rglob("*.md") if p.name not in SKIP_FILES
    )


def repo_root(start: Path) -> Path:
    """Walk up from ``start`` until we hit a directory that contains a .git."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError(f"Could not find repo root from {start}")


@lru_cache(maxsize=None)
def _basename_index(root: Path) -> dict[str, list[Path]]:
    """Index every file in the repo by basename (cached per root).

    Used to resolve bare filenames like `tweet_type_metrics_hydrator.rs`
    that are cited without their parent directory (e.g. when the parent
    was named earlier in the same paragraph).
    """
    index: dict[str, list[Path]] = {}
    for p in root.rglob("*"):
        if p.is_file() and "/.git/" not in str(p):
            index.setdefault(p.name, []).append(p)
    return index


def resolve(ref: Reference, root: Path, skill_dir: Path | None = None) -> Path | None:
    """Try a few strategies to resolve a cited path to a real file.

    1. Repo-relative: `root / ref.cited_path`.
    2. File-relative: `ref.skill_file.parent / ref.cited_path` (for refs from
       nested skill files pointing at a sibling).
    3. Skill-root-relative: `skill_dir / ref.cited_path` (for refs from a
       nested file like `tools/README.md` pointing at `references/...`).
    4. Bare-filename anywhere in the repo (only when the citation has no `/`).
    """
    repo_target = root / ref.cited_path
    if repo_target.exists():
        return repo_target

    file_relative = ref.skill_file.parent / ref.cited_path
    if file_relative.exists():
        return file_relative

    if skill_dir is not None:
        skill_relative = skill_dir / ref.cited_path
        if skill_relative.exists():
            return skill_relative

    if "/" not in ref.cited_path:
        matches = _basename_index(root).get(ref.cited_path, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Ambiguous bare basename — treat as a soft success: at least one
            # file with that name exists. The skill author can disambiguate
            # by including the parent directory if needed.
            return matches[0]

    return None


def verify(skill_dir: Path) -> tuple[int, list[tuple[Reference, str]]]:
    """Return (checked_count, failures) where each failure is (ref, reason)."""
    root = repo_root(skill_dir)
    failures: list[tuple[Reference, str]] = []
    refs: list[Reference] = []
    for md in find_skill_markdown(skill_dir):
        refs.extend(extract_references(md))

    for ref in refs:
        if resolve(ref, root, skill_dir=skill_dir) is None:
            failures.append((ref, "path does not exist"))

    return len(refs), failures


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve()
    skill_dir = here.parent.parent  # .claude/skills/x-virality/
    if argv:
        skill_dir = Path(argv[0]).resolve()

    checked, failures = verify(skill_dir)
    if failures:
        print(f"verify_refs: {len(failures)} broken reference(s) "
              f"out of {checked} checked\n")
        for ref, reason in failures:
            rel = ref.skill_file.relative_to(repo_root(skill_dir))
            print(f"  {rel}:{ref.line_no}  -> `{ref.cited_path}`  ({reason})")
        return 1

    print(f"verify_refs: OK ({checked} references checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
