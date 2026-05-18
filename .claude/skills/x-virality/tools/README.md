# Tools

Two scripts and their pytest suites. The CI workflow at `.github/workflows/verify-skill.yml` runs both on every PR that touches the skill.

## `verify_refs.py`

Walks every `.md` in the skill folder, extracts paths cited inside backticks, and asserts each one resolves to a real file in this repo. Catches the most common form of skill rot: a Rust file gets renamed, the skill still cites the old name, agents start serving outdated guidance.

Resolution strategies, in order:

1. Repo-relative (`home-mixer/scorers/weighted_scorer.rs`).
2. Skill-relative (`checklist.md` → `.claude/skills/x-virality/checklist.md`).
3. Bare filename anywhere in the repo (when no `/` in the citation).

`ROADMAP.md` is skipped — it intentionally references files for future sprints.

```bash
python .claude/skills/x-virality/tools/verify_refs.py
# verify_refs: OK (153 references checked)
```

Exit code 1 on any unresolved reference. Use this in pre-commit hooks or CI.

## `score_simulator.py`

Python re-implementation of the structure of `home-mixer/scorers/ranking_scorer.rs::compute_weighted_score` plus the diversity decay and OON factor multipliers. Lets you reason about trade-offs in a draft post by feeding in your own predicted per-action probabilities and getting a final ranking-style score back.

**Not a Phoenix clone.** Phoenix predicts the per-action probabilities; this script accepts them as inputs.

```python
from score_simulator import Candidate, PhoenixScores, ScoringWeights, score_batch

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

## Tests

```bash
pip install pytest
pytest .claude/skills/x-virality/tools/tests/ -v
```

Two suites:

- `test_score_simulator.py` — unit + regression tests that pin the formula structure (signs of weights, gating, offset, diversity decay, OON application) to the Rust source. If the production code changes shape, these tests fail loudly so we know to update both the simulator and the skill docs.
- `test_verify_refs.py` — unit tests for the path extraction + resolution logic, plus a live regression that runs `verify_refs.verify()` against the actual skill folder.

## Playwright

Not applicable. The skill is markdown + Python scripts. There is no UI to drive. If a Sprint 6 deliverable adds a web-based score-simulator playground, Playwright would belong there, not here.
