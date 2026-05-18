# Quote-Post Recipes

Target signals: `quote_score` + `quoted_click_score` + `quoted_vqv_score`.
See `home-mixer/scorers/ranking_scorer.rs` (`QuoteWeight`, `QuotedClickWeight`, `QuotedVqvWeight`).

Quote posts have their own dedicated weights — three of them. That's because a quote is more valuable than a repost: it adds context, drives traffic to the original, and lets the quoter signal endorsement or disagreement. The algorithm rewards the layered engagement.

When you write content, leave quote-friction low. When you respond to others, default to quote (not bare repost) unless you genuinely have nothing to add.

---

## Pattern 1 — One-line take above a great original

**Mechanic:** quote a strong original post with a single line that recontextualizes it.

**Template:**

> [Your one-line take.]
>
> [Quote the original.]

**Why this works:** quote-clickers want to read the original *and* your context. `quoted_click_score` triggers when they click through; `quoted_vqv_score` triggers if the quoted post has a video > `MinVideoDurationMs`. Your one-liner becomes the lens through which the original is read.

**Anti-patterns:**
- Bare repost — only fires `retweet_score`. Lower weight, no `quote_*` cascade.
- Long quote-text — readers skip your text and read the original.

---

## Pattern 2 — Disagreement frame, civilly

**Mechanic:** quote someone you respect to disagree with, with the disagreement specific enough to be useful.

**Template:**

> Pushing back on this: [your specific counter, 2-3 lines.]
>
> [Quote the original.]

**Why this works:** drives `quote_score` from your audience (they want to see whose side they're on) and `quoted_click_score` (they click through to read the original). Often picks up replies (both sides chime in) → stacks `reply_score`.

**Anti-patterns:**
- Pile-on — risks `report_score`, `block_author_score`, `mute_author_score` from the original poster's audience.
- Strawman the original — readers click through, see you mischaracterized it, and downvote.

---

## Pattern 3 — Quote-amplifying your own post with new context

**Mechanic:** quote your own earlier post when something changes that makes it relevant again.

**Template:**

> Update: [what's new, 1-2 lines.]
>
> [Quote your earlier post.]

**Why this works:** lets you re-surface content without triggering `PreviouslySeenPostsFilter` (`home-mixer/filters/previously_seen_posts_filter.rs`), because the quote post is a *new* post ID with the original embedded. `quote_score` fires, and viewers who saw the original get fresh engagement value.

**Anti-patterns:**
- Quote-amplifying your own post too soon — author-diversity decay (`home-mixer/scorers/author_diversity_scorer.rs`) punishes back-to-back.
- Quoting your own post with no new info — reads as spam, hits `grox/tasks/task_spam_detection.py`.

---

## Pattern 4 — Pattern-matching across two posts

**Mechanic:** quote one post and pair it with an unrelated screenshot/observation to surface a pattern.

**Template:**

> [The pattern you're naming, 1 line.]
>
> [Quote one post + image / second observation.]

**Why this works:** the recontextualization rewards `dwell_time` (readers stop to understand) plus `quote_score`. If your second observation is itself shareable, you get `share_via_copy_link_score` too.

**Anti-patterns:**
- Forced pattern — readers don't see the connection, dwell drops.
- Pattern that mocks specific people — drives blocks/reports.

---

## Pattern 5 — Quoting a video post to recommend it

**Mechanic:** quote a video post with text that nudges the reader to watch.

**Template:**

> [Specific tease about what's in the video, 1 line.]
>
> [Quote video post.]

**Why this works:** drives `quoted_vqv_score` (the quoted video gets a Video Quality View). Note: the gating from `ranking_scorer.rs:139-144` — `EnableQuotedVqvDurationCheck` means the quoted video has to exceed `MinVideoDurationMs` or the `quoted_vqv` weight zeros out. Pick a substantive video, not a 2-second loop.

**Anti-patterns:**
- Spoiling the video in your text — readers don't open it, `quoted_vqv_score` doesn't fire.
- Quoting a video that's under threshold — wasted weight.

---

## How quote signals stack

A single quote post fires:

- `quote_score` (the quote action itself)
- `quoted_click_score` (clicking through to the original)
- `quoted_vqv_score` (if the quoted post is a qualifying video)

That's three positive weights from one engagement chain. By comparison, a bare retweet fires `retweet_score` — one weight, lower magnitude. Default to quote.

## Output contract (when invoked)

When the user asks you to draft a quote post, return:

1. The chosen pattern.
2. The quote text (your line(s) above the embed).
3. Why the original deserves the quote treatment vs a bare repost.
4. Expected signal cascade: which `quote_*` fields you expect to fire.
5. If the original is a video: confirm duration > `MinVideoDurationMs` (or note it as a risk).
