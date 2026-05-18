# X Virality Skill

A portable skill for AI agents (Claude Code, Codex, Tota Agent, etc.) that teaches them to write X (Twitter) content tuned to the public X For You algorithm in this repository.

The skill is **source-grounded**: every claim points back to a file in `home-mixer/`, `phoenix/`, `thunder/`, `grox/`, or `candidate-pipeline/`. When the algorithm changes, the skill should change with it.

## Files

```
.claude/skills/x-virality/
├── SKILL.md                          # Main entry, loaded by the agent
├── checklist.md                      # Pre-publish quick check
├── README.md                         # (this file) install + scope
├── ROADMAP.md                        # Full sprint plan (acts as issue tracker)
├── references/
│   ├── algorithm-signals.md          # Every signal, mapped to source
│   ├── scoring-weights.md            # The weighted-score formula
│   ├── filters-and-vf.md             # What drops reach to zero
│   └── recipes/
│       └── reply-bait.md             # Recipe library — by target signal
└── tools/
    ├── README.md
    ├── verify_refs.py                # CI: every cited source path still exists
    ├── score_simulator.py            # Heuristic weighted-score predictor
    └── tests/
        ├── conftest.py
        ├── test_verify_refs.py
        └── test_score_simulator.py
```

## Installing for each agent

### Claude Code

This repo follows the [Claude Code skills](https://code.claude.com/docs) convention. The skill auto-loads when this repo is opened:

- The `name` and `description` in `SKILL.md`'s YAML frontmatter are used to decide when to invoke it.
- Reference files (`references/*.md`, `checklist.md`) are read on demand.

You can also install the skill globally:

```bash
cp -R .claude/skills/x-virality ~/.claude/skills/
```

### Codex

Add the following to your `AGENTS.md` (or equivalent system prompt):

```
When working on X (Twitter) content optimization, follow:
  .claude/skills/x-virality/SKILL.md
References:
  - .claude/skills/x-virality/references/algorithm-signals.md
  - .claude/skills/x-virality/references/scoring-weights.md
  - .claude/skills/x-virality/references/filters-and-vf.md
  - .claude/skills/x-virality/checklist.md
```

### Tota Agent

Register the skill folder as a knowledge source. Tota will index the markdown and the frontmatter description routes invocations.

If Tota uses a different schema (e.g. `tota.skill.json`), generate it from `SKILL.md` — the description and references blocks are the inputs Tota needs. See the planned issue **[Sprint 5] Tota Agent variant**.

## Scope

This skill is for **organic content** on X. It does not cover:
- X Ads (campaigns, auctions, bidding) — that's a separate playbook.
- Bot / automation (against ToS).
- Off-platform amplification (cross-posting, embeds, etc.).
- Account safety / appeals.

For algorithm changes outside this repo (e.g. live API behavior X.com ships that isn't in OSS), prefer the OSS source as the canonical reference for this skill.

## Roadmap

GitHub Issues is currently disabled on this repo, so the canonical roadmap lives in `ROADMAP.md` inside this folder. It's structured as one checklist per sprint and is meant to be mirrored to GitHub Issues 1:1 the moment Issues is enabled.

- **Sprint 1** — Foundation ✅ (PR #1)
- **Sprint 2** — Content recipes & templates 🚧 (reply-bait shipped)
- **Sprint 3** — Video & multimedia playbook
- **Sprint 4** — Distribution & network growth
- **Sprint 5** — Risk & anti-patterns
- **Sprint 6** — Tooling & multi-agent integrations 🚧 (verify_refs, score_simulator, CI shipped)

## Tests

```bash
pip install pytest
python .claude/skills/x-virality/tools/verify_refs.py
pytest .claude/skills/x-virality/tools/tests/ -v
```

CI runs both on every PR that touches the skill (`.github/workflows/verify-skill.yml`).
