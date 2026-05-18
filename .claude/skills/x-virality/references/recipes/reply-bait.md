# Reply-Bait Recipes

Target signal: `reply_score` (and `quote_score` as a frequent co-trigger).
See `home-mixer/scorers/ranking_scorer.rs` and `home-mixer/scorers/weighted_scorer.rs`.

Replies are one of the highest-weight positive signals in the formula. They also feed a second-order loop: every reply on your post triggers `reply_ranking` for that conversation (`grox/plans/plan_reply_ranking.py`), and your replies *to* those commenters earn their own ranking pass.

This file is a working library — add new patterns when one ships and works.

---

## Pattern 1 — The half-finished list

**Mechanic:** start a list and stop one or two items short. Readers complete it for you in replies.

**Template:**

> Things that are obvious in hindsight but everyone gets wrong the first time:
>
> 1. [concrete, specific item]
> 2. [concrete, specific item]
> 3. [concrete, specific item]
> 4. [...]

**Why this works for the algorithm:** each reply adds an item, which prompts more replies arguing/refining/adding. `reply_score` stacks; `dwell_score` also rises because the post + thread reads as a long-form list. Negative signals are low because readers self-select into the topic.

**Anti-patterns:**
- Listing 10 items already — no room for replies.
- Vague items ("good design", "thinking clearly") — invites disagreement on definition, not contribution.
- Filling out the list in subsequent tweets in the same thread — `DedupConversationFilter` (`home-mixer/filters/dedup_conversation_filter.rs`) will collapse parallel branches anyway.

---

## Pattern 2 — Mild contrarian take, civil framing

**Mechanic:** stake a position most of your audience disagrees with, but frame it so disagreement is invited, not attacked.

**Template:**

> [Widely held belief X] is mostly wrong because [concrete reason]. I used to believe X. What changed my mind was [specific experience/data].

**Why this works:** drives `reply_score` from disagreers and `quote_score` from people building on it. The "I used to believe X" framing is critical — it signals you've considered the other side, which lowers `not_interested_score`, `block_author_score`, `mute_author_score`. Pure rage-bait does the opposite.

**Anti-patterns:**
- Attacking identity groups → spikes `block_author`, `mute_author`, `report` (heavy negative weights, `home-mixer/scorers/ranking_scorer.rs` `negative_sum`).
- Vague contrarian ("everyone is wrong about everything") → no specific reply hook.
- Subtweeting a named person → drives reports + adjacent author drama, often picks up `DO_NOT_AMPLIFY` (`home-mixer/scored_posts_server.rs::safety_label_to_proto`).

---

## Pattern 3 — Open question with a strong prior

**Mechanic:** ask a question but reveal what you think the answer is. Readers reply to confirm, refine, or push back.

**Template:**

> Why does [observation] keep happening?
>
> My current theory: [specific hypothesis].
>
> What am I missing?

**Why this works:** "What am I missing?" is a near-universal reply trigger — the cost of replying drops because the asker has already framed the question. The strong prior gives commenters a target to react to.

**Anti-patterns:**
- Pure open-ended question with no prior → fewer replies because the cost of formulating one is higher.
- "Thoughts?" by itself reads as low-effort; pairs poorly with the spam classifier (`grox/tasks/task_spam_detection.py`).

---

## Pattern 4 — Specific number, missing context

**Mechanic:** state a precise, surprising number without explaining why. The question of "wait, why?" is implicit.

**Template:**

> [X percent] of [specific group] [does specific thing]. [One-line reason or none.]

**Why this works:** specificity is a stop-scroll signal — it triggers `dwell_score` (`home-mixer/scorers/weighted_scorer.rs:59-62`). The implicit "why?" drives replies asking for the source or pushing back.

**Anti-patterns:**
- Made-up numbers — Community Notes (`NSFA_COMMUNITY_NOTE` in `home-mixer/scored_posts_server.rs::safety_label_to_proto`) can flag the post NSFA and hard-limit it.
- Numbers with no surprise value ("90% of devs use git") — no reply trigger.

---

## Pattern 5 — Fill-in-the-blank

**Mechanic:** explicitly invite a completion.

**Template:**

> Underrated skill in [field]: ___

**Why this works:** literal lowest-friction reply. Every reply is a one-word/one-phrase completion. High `reply_score`, low `dwell_score` per post (compensated by reply volume).

**Anti-patterns:**
- Over-used framings ("unpopular opinion: ___") read as engagement-bait and hit the spam screen.
- Filling in your own answer in the first reply — kills the format.

---

## Cadence reminder

Author-diversity decay (`home-mixer/scorers/author_diversity_scorer.rs`) means stacking five reply-bait posts in an hour competes against itself. Pick one reply-bait per day, max. Save the others for follow-magnet or share recipes.

## Output contract (when invoked)

When the user asks you to draft a reply-bait post, return:

1. The chosen pattern (number + name from above).
2. The drafted post (≤280 chars).
3. The target signal: always `reply_score`, plus likely co-triggers.
4. Risk flags: any pattern-specific anti-patterns to watch.
5. First-60-minute follow-up plan: which replies to engage with first, what to say to keep the conversation alive (boosts your replies' own ranking via `plan_reply_ranking.py`).
