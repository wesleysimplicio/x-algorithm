# Share Recipes

Target signals: `share_score`, `share_via_dm_score`, `share_via_copy_link_score`.
See `home-mixer/scorers/ranking_scorer.rs` (`ShareWeight`, `ShareViaDmWeight`, `ShareViaCopyLinkWeight`).

Three different share fields means the algorithm distinguishes *how* people share. DM share is the social-proof signal: someone sends it to a friend. Copy-link share is the off-platform signal: someone takes it to Slack, iMessage, email. Both are strong positive weights.

Optimizing for shares is mostly about making the post be *about* someone the reader knows, or *useful enough* that withholding it would feel selfish.

---

## Pattern 1 — Insider knowledge worth forwarding

**Mechanic:** state a non-obvious truth that an insider in some field would recognize as accurate. Outsiders DM it to insiders to ask "is this real?"; insiders DM it to other insiders saying "ha, true."

**Template:**

> [Field/role] thing nobody outside [field] understands: [the specific truth, 1-2 lines.]

**Why this works:** triggers `share_via_dm_score` because the post becomes a probe. Insiders forward to confirm with peers; outsiders forward to ask "is this how it actually is?"

**Anti-patterns:**
- Generic inside-baseball ("traders work long hours") — not surprising enough to forward.
- Confidential / leaked content — risks PTOS policy via `grox/tasks/task_safety_ptos_policy.py`.

---

## Pattern 2 — Useful list / cheat-sheet

**Mechanic:** post a list that pays off in practical use. Reads as a screenshot people will save.

**Template:**

> [N] things you should know about [topic]:
>
> 1. [Practical fact 1]
> 2. [Practical fact 2]
> 3. [Practical fact 3]
> 4. [Practical fact 4]
> 5. [Practical fact 5]

**Why this works:** triggers `share_via_copy_link_score` because readers copy the link to put it in a doc / Slack channel / saved-for-later. Also high `photo_expand_score` if the list is in an image and `dwell_score` from the time spent reading.

**Anti-patterns:**
- Generic ("be kind, work hard") — nothing to save.
- Too long (>10 items) — copy-link share rate drops because nobody screenshots a wall.

---

## Pattern 3 — The "wait until you hear" gossip frame

**Mechanic:** describe an event in a way that makes the reader feel like they got a story they want to retell.

**Template:**

> [Compact narrative setup, 2 lines.]
>
> [The turn, 1 line.]
>
> [The kicker, 1 line.]

**Why this works:** triggers `share_via_dm_score` heavily — readers DM these to friends. The 3-beat structure is naturally retellable.

**Anti-patterns:**
- Naming specific people negatively — drives reports, mutes, blocks → `block_author_score`, `mute_author_score`, `report_score` (negative weights).
- Mocking identity groups — `DO_NOT_AMPLIFY` label risk (`home-mixer/scored_posts_server.rs::safety_label_to_proto`).

---

## Pattern 4 — Surprising chart / screenshot with one-line caption

**Mechanic:** post a screenshot that pays off without needing the body text. Body text deepens the read.

**Template:**

> [One-line caption above the image that makes the reader want to see the chart.]
>
> [Chart / screenshot.]
>
> [Optional: 2-3 lines of context below.]

**Why this works:** images trigger `photo_expand_score` and screenshots are the most-shared format because they preserve well in DM previews and Slack unfurls — driving `share_via_copy_link_score`.

**Anti-patterns:**
- Image is from a paywalled source — readers who hit the source bail; long-term, reduces follow conversion.
- Image is misleading — Community Note risk (`NSFA_COMMUNITY_NOTE`).

---

## Pattern 5 — Tactical answer to a common question

**Mechanic:** answer a question your audience asks regularly, in a form they can forward instead of typing the answer themselves.

**Template:**

> [Frame the common question.]
>
> [Tactical answer, 3-5 lines, with one specific recommendation.]

**Why this works:** triggers `share_via_dm_score` because the next time someone asks the question, your followers send the post instead of typing. Also drives `share_via_copy_link_score` for saved-answer use.

**Anti-patterns:**
- Vague answer ("it depends") — nothing to forward.
- Answer that requires more context than fits — readers screenshot a section, you lose attribution + clicks.

---

## DM share vs copy-link — which to optimize for

- **`share_via_dm_score`**: insider, gossip, "send to friend" content. Personal, social-proof.
- **`share_via_copy_link_score`**: useful, durable, off-platform reusable. Lists, cheat-sheets, charts.
- **`share_score`**: catch-all, fires for both.

Different posts hit different shares — pick one explicitly. A post optimized for both rarely wins either.

## Output contract (when invoked)

When the user asks you to draft a share-bait post, return:

1. The chosen pattern (number + name).
2. The drafted post.
3. The target share type: DM, copy-link, or both.
4. Why the reader would share this (insider proof / save for later / forward as answer / etc.).
5. Risk flags: PTOS, Community Note, brand-safety concerns from `home-mixer/models/brand_safety.rs`.
