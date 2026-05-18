# X Virality Skill — Sprint Roadmap

GitHub Issues is currently disabled on this repo, so this file is the canonical map of all sprint work. When Issues is enabled, mirror each `- [ ]` line below as a GitHub issue, labeled `sprint-N` + the matching area label, and reference back here.

Status legend: ✅ done · 🚧 in progress · ⏳ planned

---

## Epic — X Virality Skill

Ship a portable skill (`.claude/skills/x-virality/`) any AI agent can load to write X content tuned to the For You algorithm in this repo. Every claim source-grounded.

**Definition of done**
1. `SKILL.md` with frontmatter, playbook, output contract. ✅
2. References cover every signal/weight/filter/VF label/Grox screen, mapped to source. ✅
3. Score simulator that takes a draft → predicted weighted-score profile. 🚧
4. Install paths for Claude Code, Codex, Tota Agent. (Claude: ✅, others: ⏳)
5. Measurement loop: post-publish engagement → feedback. ⏳
6. CI `verify-skill-refs` confirms every cited source path still exists. 🚧

---

## Sprint 1 — Foundation ✅

Shipped in PR #1 (merged).

- ✅ **S1-1** Skill scaffolding + `SKILL.md` with YAML frontmatter + playbook + output contract — `.claude/skills/x-virality/SKILL.md`.
- ✅ **S1-2** Reference: algorithm signals catalog — `references/algorithm-signals.md`.
- ✅ **S1-3** Reference: scoring weights formula — `references/scoring-weights.md`.
- ✅ **S1-4** Reference: filters + VF labels — `references/filters-and-vf.md`.
- ✅ **S1-5** Pre-publish checklist — `checklist.md`.
- ✅ **S1-6** README with install paths for Claude Code / Codex / Tota — `README.md`.

---

## Sprint 2 — Content recipes & templates

Goal: a library of copywriting recipes mapped to specific positive-weight signals. Each recipe = one optimization target, one structural template, ≥3 example posts, anti-patterns.

- ✅ **S2-1** Reply-bait recipe library (target: `reply_score`) — `references/recipes/reply-bait.md`. Shipped.
- ⏳ **S2-2** Dwell-time long-form recipe library (target: `dwell_score` + `dwell_time`) — `references/recipes/dwell.md`.
- ⏳ **S2-3** Share-bait recipes (target: `share_via_dm_score` + `share_via_copy_link_score`) — `references/recipes/share.md`.
- ⏳ **S2-4** Follow-magnet recipes (target: `follow_author_score`) — `references/recipes/follow-magnet.md`.
- ⏳ **S2-5** Quote-post recipes (target: `quote_score` + `quoted_click_score` + `quoted_vqv_score`) — `references/recipes/quote.md`.
- ⏳ **S2-6** Thread structure playbook (chaining, hook-per-tweet, dedup-conversation awareness) — `references/recipes/threads.md`.

**Acceptance per recipe:** target signal cited; structural template; ≥3 example posts; risk callouts; checklist excerpt.

---

## Sprint 3 — Video & multimedia playbook

Goal: turn the `tweet_type_metrics_hydrator.rs` duration buckets and `vqv_weight` gating into actionable formats.

- ⏳ **S3-1** Video duration playbook (≤10s, 10-60s, >60s buckets, VQV gating) — `references/video-playbook.md`.
- ⏳ **S3-2** Image / photo composition for `photo_expand_score` (zoom payoff, framing) — `references/photo-playbook.md`.
- ⏳ **S3-3** Multimodal post embedding strategy (alignment to Grox v5 multimodal embedder) — `references/multimodal-playbook.md`.

---

## Sprint 4 — Distribution & network growth

Goal: leverage the OON factor, mutual-follow Jaccard, and follower-bucket features.

- ⏳ **S4-1** Mutual-follow Jaccard strategy (MinHash, niche-cluster building) — `references/distribution/mutual-follow.md`.
- ⏳ **S4-2** OON expansion playbook (escape your bubble safely) — `references/distribution/oon-expansion.md`.
- ⏳ **S4-3** New-user playbook (`is_eligible_new_user` window + `NEW_USER_OON_WEIGHT_FACTOR`) — `references/distribution/new-user.md`.
- ⏳ **S4-4** X Premium / subscription playbook (`SUBSCRIPTION_POST` flag, ranking implications) — `references/distribution/premium.md`.

---

## Sprint 5 — Risk & anti-patterns

Goal: turn VF labels, brand-safety verdicts, spam classifier, and cadence rules into avoidance guides.

- ⏳ **S5-1** VF label avoidance guide (every label in `scored_posts_server.rs::safety_label_to_proto`) — `references/risk/vf-labels.md`.
- ⏳ **S5-2** Spam classifier + brand-safety verdict guide (`grox/tasks/task_spam_detection.py`, `models/brand_safety.rs`) — `references/risk/spam-and-brand-safety.md`.
- ⏳ **S5-3** Author-diversity decay & cadence guide (`AuthorDiversityDecay`, `AuthorDiversityFloor`) — `references/risk/cadence.md`.
- ⏳ **S5-4** Age / freshness + first-hour playbook (`AgeFilter`, age buckets in `tweet_type_metrics_hydrator.rs`) — `references/risk/freshness.md`.

---

## Sprint 6 — Tooling & multi-agent integrations

Goal: testable artifacts so the skill stays honest as the codebase evolves.

- ✅ **S6-1** `tools/score_simulator.py` — heuristic that takes a draft (text, media, duration, in_network flag, predicted action probabilities) and returns a weighted-score profile mirroring `ranking_scorer.rs::compute_weighted_score`. Pytest unit tests covering vqv gating, offset, diversity decay, OON factor, sign structure. Shipped.
- ✅ **S6-2** `tools/verify_refs.py` — scans every `.md` in the skill, extracts cited paths, asserts each resolves (repo-relative, skill-relative, or bare-filename anywhere). Pytest unit tests + live regression. Shipped.
- ⏳ **S6-3** CLI for the pre-publish checklist (interactive, walks through `checklist.md`).
- ⏳ **S6-4** Codex `AGENTS.md` variant — generated from `SKILL.md` frontmatter.
- ⏳ **S6-5** Tota Agent skill packaging (whatever Tota's schema is — investigate, then ship).
- ⏳ **S6-6** Post-publish measurement loop — given a posted tweet ID and the X API or copy-pasted metrics, compare predicted vs actual signal hits; surface drift.
- ✅ **S6-7** CI workflow that runs `verify_refs` + pytest on every PR — `.github/workflows/verify-skill.yml`. Shipped.

---

## Out of scope (do not promote into a sprint)

- Building a Phoenix model clone. The simulator is heuristic and explicit about it.
- Tracking runtime parameter numeric values. Weights are runtime configs — teach structure, not numbers.
- X Ads campaign optimization (separate playbook).
- Automation / bots (against ToS).
- Off-platform amplification.

---

## Mirror to GitHub Issues (when enabled)

When `Settings → Features → Issues` is turned on:

1. Create one **Epic** issue (label: `epic`) using the section above.
2. Create one issue per `S*-*` bullet, with labels: `sprint-N`, `area:skill` (docs/recipes) or `area:tooling` (S6 items).
3. Close S1 issues immediately (done in PR #1).
4. Replace the `🚧 (Landing in this PR)` markers with PR links.
