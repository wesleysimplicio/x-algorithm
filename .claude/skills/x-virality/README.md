# X Virality Skill

A portable skill for AI agents (Claude Code, Codex, Tota Agent, etc.) that teaches them to write X (Twitter) content tuned to the public X For You algorithm in this repository.

The skill is **source-grounded**: every claim points back to a file in `home-mixer/`, `phoenix/`, `thunder/`, `grox/`, or `candidate-pipeline/`. When the algorithm changes, the skill should change with it — `tools/verify_refs.py` enforces this in CI.

## Files

```
.claude/skills/x-virality/
├── SKILL.md                          # Main entry, loaded by the agent
├── checklist.md                      # Pre-publish quick check
├── ROADMAP.md                        # Sprint plan (all 6 sprints ✅)
├── README.md                         # (this file) install + scope
├── references/
│   ├── algorithm-signals.md          # Every signal, mapped to source
│   ├── scoring-weights.md            # The weighted-score formula
│   ├── filters-and-vf.md             # What drops reach to zero
│   ├── video-playbook.md             # VQV gating + duration buckets
│   ├── photo-playbook.md             # photo_expand_score composition
│   ├── multimodal-playbook.md        # Text + media alignment for retrieval
│   ├── recipes/
│   │   ├── reply-bait.md             # → reply_score
│   │   ├── dwell.md                  # → dwell_score + dwell_time
│   │   ├── share.md                  # → share_via_dm/copy_link
│   │   ├── follow-magnet.md          # → follow_author_score
│   │   ├── quote.md                  # → quote_score cascade
│   │   └── threads.md                # Thread structure
│   ├── distribution/
│   │   ├── mutual-follow.md          # MinHash Jaccard strategy
│   │   ├── oon-expansion.md          # Escape OON penalty
│   │   ├── new-user.md               # New-account window
│   │   └── premium.md                # X Premium / subscription
│   └── risk/
│       ├── vf-labels.md              # Every VF label
│       ├── spam-and-brand-safety.md  # Spam classifier + MediumRisk
│       ├── cadence.md                # Author-diversity decay
│       └── freshness.md              # Age filter + age buckets
└── tools/
    ├── README.md
    ├── verify_refs.py                # Every cited source path exists
    ├── score_simulator.py            # Heuristic weighted-score predictor
    ├── checklist_cli.py              # Interactive checklist walker
    ├── generate_agents.py            # Regenerate AGENTS.md + tota.skill.json
    ├── measurement_loop.py           # Predicted-vs-actual engagement loop
    └── tests/
        ├── conftest.py
        ├── test_verify_refs.py
        ├── test_score_simulator.py
        ├── test_checklist_cli.py
        ├── test_generate_agents.py
        └── test_measurement_loop.py
```

Plus, generated at repo root:

```
AGENTS.md           # Codex entry point
tota.skill.json     # Generic JSON skill manifest
```

## Installing for each agent

### Claude Code

The skill auto-loads from this repo when you open it in Claude Code. The frontmatter `description` in `SKILL.md` routes invocations.

You can also install globally:

```bash
cp -R .claude/skills/x-virality ~/.claude/skills/
```

### Codex

`AGENTS.md` at the repo root is the Codex entry point. It points at `SKILL.md` and lists every reference. Codex agents read this on session start.

`AGENTS.md` is generated from `SKILL.md`'s frontmatter — don't edit it by hand. Edit `SKILL.md`, then run:

```bash
python .claude/skills/x-virality/tools/generate_agents.py
```

### Tota Agent (and other generic agents)

`tota.skill.json` at the repo root is a generic JSON skill manifest:

```json
{
  "name": "x-virality",
  "description": "...",
  "entrypoint": ".claude/skills/x-virality/SKILL.md",
  "references": [...],
  "tools": [...],
  "checklist": ".claude/skills/x-virality/checklist.md",
  "roadmap": ".claude/skills/x-virality/ROADMAP.md",
  "schema_version": 1
}
```

Tota or any agent that reads a JSON skill schema can ingest this.

Like `AGENTS.md`, this file is generated — run `generate_agents.py` after editing `SKILL.md`.

## Scope

This skill is for **organic content** on X. It does not cover:
- X Ads (campaigns, auctions, bidding) — separate playbook.
- Bot / automation (against ToS).
- Off-platform amplification.
- Account safety / appeals.

For algorithm changes outside this repo (live API behavior X.com ships that isn't in OSS), prefer the OSS source as the canonical reference for this skill.

## Roadmap status

All Sprint 1-6 deliverables are ✅. See `ROADMAP.md` for the full map. GitHub Issues mirror is pending — Issues is currently disabled on this repo (`POST /issues` returns `410`). When it's re-enabled, each `S*-*` bullet in `ROADMAP.md` maps directly to one issue.

## Tests

```bash
pip install pytest
python .claude/skills/x-virality/tools/verify_refs.py
python .claude/skills/x-virality/tools/generate_agents.py --check
pytest .claude/skills/x-virality/tools/tests/ -v
```

CI runs all three on every PR that touches the skill (`.github/workflows/verify-skill.yml`).

## Playwright

Not applicable. The skill is markdown + Python scripts; no UI to drive. If a future feature adds a web-based score-simulator playground, Playwright belongs there.
