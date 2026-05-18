# Tools

Five scripts plus pytest suites. The CI workflow at `.github/workflows/verify-skill.yml` runs all checks on every PR that touches the skill.

## `verify_refs.py`

Walks every `.md` in the skill folder, extracts paths cited inside backticks, and asserts each one resolves to a real file in this repo. Catches the most common form of skill rot: a Rust file gets renamed, the skill still cites the old name, agents start serving outdated guidance.

Resolution strategies, in order:

1. Repo-relative (`home-mixer/scorers/weighted_scorer.rs`).
2. File-relative (`checklist.md` cited from `SKILL.md`).
3. Skill-root-relative (`references/recipes/dwell.md` cited from `tools/README.md`).
4. Bare filename anywhere in the repo (when no `/` in the citation).

`ROADMAP.md` is skipped — it intentionally references files for future sprints.

```bash
python .claude/skills/x-virality/tools/verify_refs.py
# verify_refs: OK (320 references checked)
```

Exit code 1 on any unresolved reference. Use in pre-commit hooks or CI.

## `score_simulator.py`

Python re-implementation of the structure of `home-mixer/scorers/ranking_scorer.rs::compute_weighted_score` plus the diversity decay and OON factor multipliers. Lets you reason about trade-offs in a draft post by feeding in your own predicted per-action probabilities and getting a final ranking-style score back.

**Not a Phoenix clone.** Phoenix predicts the per-action probabilities; this script encodes the formula on top.

```python
from score_simulator import Candidate, PhoenixScores, score_batch

draft = Candidate(
    scores=PhoenixScores(reply=0.05, dwell=0.4, follow_author=0.01),
    in_network=True,
    video_duration_ms=None,
    author_id=42,
)

reports = score_batch([draft])
print(reports[0].explain())
```

The default `ScoringWeights` encode the *prioritization* documented in `references/scoring-weights.md` (follow > reply > dwell > like, with heavy negative weights on report / block / mute), not production numeric values. Override the weights for your context.

## `checklist_cli.py`

Interactive walker for `checklist.md`. Walks every `- [ ]` item, captures pass/fail/skip, prints a structured verdict.

```bash
python .claude/skills/x-virality/tools/checklist_cli.py
# Interactive: walks each item, prompts p/f/s.

python .claude/skills/x-virality/tools/checklist_cli.py --non-interactive --auto-pass
# CI smoke: auto-pass everything, just validates the checklist parses.

python .claude/skills/x-virality/tools/checklist_cli.py --json
# Emit JSON for programmatic consumption.
```

Exit code 1 if ≥ 2 items failed (the checklist's own rewrite threshold).

## `generate_agents.py`

Regenerates the two install artifacts at the repo root from `SKILL.md`'s YAML frontmatter:

- `AGENTS.md` — Codex / CLI agent entry point.
- `tota.skill.json` — Generic JSON skill manifest for Tota Agent and any agent ingesting JSON schemas.

```bash
python .claude/skills/x-virality/tools/generate_agents.py
# Writes both files. No-op if already in sync.

python .claude/skills/x-virality/tools/generate_agents.py --check
# CI mode: exit non-zero if either file is out of sync. Used by .github/workflows/verify-skill.yml.
```

**Edit `SKILL.md`, then regenerate.** Don't hand-edit `AGENTS.md` or `tota.skill.json`.

## `measurement_loop.py`

Records predicted vs actual engagement per post, aggregates drift over time. Closes the feedback loop: as you accumulate measurements, you learn which signals the skill's heuristics over- or under-predict, which informs updates to the recipes and scoring discussion.

```bash
# After posting and waiting 24h, capture analytics:
python .claude/skills/x-virality/tools/measurement_loop.py record \
    --post-id 1234567890 \
    --predictions pred.json \
    --actuals actual.json

# Aggregate across all recorded posts:
python .claude/skills/x-virality/tools/measurement_loop.py summary
python .claude/skills/x-virality/tools/measurement_loop.py summary --json
```

Logs persist to `.claude/skills/x-virality/measurements/<post_id>.json`.

The predictions file should map Phoenix prediction-field names to probabilities:
```json
{"reply": 0.05, "favorite": 0.3, "follow_author": 0.01, ...}
```

The actuals file should map X-analytics field names to counts:
```json
{"replies": 12, "likes": 80, "new_follows": 3, ...}
```

The mapping between the two is defined in `measurement_loop.SIGNAL_MAP`.

## Tests

```bash
pip install pytest
pytest .claude/skills/x-virality/tools/tests/ -v
```

Five suites, 82 cases:

- `test_verify_refs.py` — unit tests for path extraction + resolution; live regression against the actual skill.
- `test_score_simulator.py` — unit + regression tests pinning the formula structure to the Rust source (signs of weights, gating, offset, diversity decay, OON application).
- `test_checklist_cli.py` — parser tests, walk semantics, threshold logic, CLI integration.
- `test_generate_agents.py` — frontmatter parsing, rendering of AGENTS.md and tota.skill.json, drift detection.
- `test_measurement_loop.py` — drift computation, persistence round-trips, aggregation semantics, CLI integration.

## Playwright

Not applicable. The skill is markdown + Python scripts. No UI to drive. If a future Sprint deliverable adds a web-based score-simulator playground, Playwright would belong there, not here.
