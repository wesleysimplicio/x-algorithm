# X Virality Skill

A portable skill for AI agents (Claude Code, Codex, Tota Agent, etc.) that teaches them to write X (Twitter) content tuned to the public X For You algorithm in this repository.

The skill is **source-grounded**: every claim points back to a file in `home-mixer/`, `phoenix/`, `thunder/`, `grox/`, or `candidate-pipeline/`. When the algorithm changes, the skill should change with it.

## Files

```
.claude/skills/x-virality/
├── SKILL.md                          # Main entry, loaded by the agent
├── checklist.md                      # Pre-publish quick check
├── README.md                         # (this file) install + scope
├── references/
│   ├── algorithm-signals.md          # Every signal, mapped to source
│   ├── scoring-weights.md            # The weighted-score formula
│   └── filters-and-vf.md             # What drops reach to zero
└── tools/
    └── (planned — see GitHub issues)
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

Tracked as GitHub issues, organized by sprint. See:
- **Epic**: `[Epic] X Virality Skill — Master Tracker`
- **Sprint 1**: Foundation (this initial commit)
- **Sprint 2-6**: Recipes, video playbook, distribution, risk, tooling, multi-agent variants

Issue list: `https://github.com/wesleysimplicio/x-algorithm/issues`
