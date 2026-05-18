# Dwell-Time Recipes

Target signals: `dwell_score` + `dwell_time` (continuous).
See `home-mixer/scorers/ranking_scorer.rs` (`DwellWeight`, `ContDwellTimeWeight`).

Dwell is the rare signal you control end-to-end. Replies, shares, follows depend on the reader acting. Dwell only requires that they don't scroll past. The negative twin `not_dwelled_score` is also one of the heaviest negative weights, so dwell is doubly leveraged: hitting it adds to your score, missing it subtracts.

---

## Pattern 1 — The mini-essay (1000-1500 chars)

**Mechanic:** post a self-contained short essay that earns each paragraph. Single tweet, no thread.

**Template:**

> [Concrete claim in 1 line.]
>
> [Setup paragraph: 2-3 lines naming the problem.]
>
> [Body paragraph: 3-5 lines of specific reasoning, with one named example.]
>
> [Pivot or counter: 1-2 lines acknowledging the other side.]
>
> [Payoff: 1 line that makes the reader feel something concrete.]

**Why this works for the algorithm:** longer text raises `dwell_time` linearly while `dwell_score` (binary) is already a hit. The transformer sees the post-length feature via `tweet_type_metrics_hydrator.rs` ranging implicitly through media + text density.

**Anti-patterns:**
- Wall of text with no breaks — readers scroll past before dwelling, triggering `not_dwelled_score`.
- Pure rant — readers leave at the first turn-off, dwell drops, and you risk `block_author_score` / `mute_author_score`.
- Saving the payoff for a thread — `DedupConversationFilter` (`home-mixer/filters/dedup_conversation_filter.rs`) often collapses parallel branches, and viewers may never load the continuation.

---

## Pattern 2 — Numbered breakdown in one tweet

**Mechanic:** a list of 4-7 short numbered items, each ≤2 lines, in a single tweet.

**Template:**

> [Topic] in 5 [units]:
>
> 1. [Item — 1 line.]
> 2. [Item — 1-2 lines.]
> 3. [...]
> 4. [...]
> 5. [...]

**Why this works:** structured content invites readers to scan all items. Each item is a checkpoint — scanning all 5 takes longer than reading prose of the same length. Drives `dwell_time` without requiring narrative continuity.

**Anti-patterns:**
- Items too short ("1. Speed. 2. Quality. 3. Cost.") — scans in 2 seconds, dwell barely registers.
- Items too long — readers bail at item 3.
- More than 7 items — return on dwell diminishes; consider a thread instead.

---

## Pattern 3 — Anatomy of [thing]

**Mechanic:** dissect one object/event/decision in detail. Readers stay because each detail is novel.

**Template:**

> Anatomy of [specific event/object/decision]:
>
> [Detail 1] — [why it matters in 1 line]
> [Detail 2] — [why it matters in 1 line]
> [Detail 3] — [why it matters in 1 line]
> [Detail 4] — [why it matters in 1 line]
>
> [Synthesis: what the details together reveal.]

**Why this works:** dissection format primes the reader to expect surprises. Each new detail keeps them in the dwell window. Cumulative density beats narrative pace for the algorithm's dwell measurement.

**Anti-patterns:**
- Generic details ("it had a meeting" / "they made decisions") — kills dwell.
- Missing the synthesis line — readers leave without the payoff, lowering `dwell_time` continuous score.

---

## Pattern 4 — Before / after, then the part most people miss

**Mechanic:** show a transition, then surface what changed underneath that nobody talks about.

**Template:**

> Before: [concrete observation.]
> After: [concrete observation.]
>
> What most people miss: [the actual driver of the change, 2-3 lines.]

**Why this works:** the before/after sets up curiosity, the third frame resolves it. Readers stay through the resolution. This pattern hits `dwell_score` and often `quote_score` because the third frame is quotable on its own.

**Anti-patterns:**
- Obvious "what most people miss" content — readers feel cheated, dwell drops.
- Three before/after pairs in a row — overworks the format, readers tune out.

---

## Pattern 5 — Annotated screenshot

**Mechanic:** post an image with text in the body that annotates / contextualizes the image. Image makes them open the post, text makes them stay.

**Template:**

> [Stop-scroll caption above the image — 1 line, makes the reader want to see what's annotated.]
>
> [Image with the actual content.]
>
> [Body text below: 3-5 lines explaining what to notice in the image, where to look, what it means.]

**Why this works:** `photo_expand_score` triggers when the reader taps to enlarge, AND `dwell_time` racks up while they read the explanation. Combining text + media earns two positive weights at once. The Grox multimodal embedder (`grox/embedder/multimodal_post_embedder_v5.py`) generates a richer joint representation, which helps retrieval find your post for more viewers.

**Anti-patterns:**
- Image without text — `dwell_time` is short.
- Text that ignores the image — `photo_expand_score` doesn't get the dwell boost.
- Screenshots of someone else's text without attribution — risks `NSFA_COMMUNITY_NOTE` (`home-mixer/scored_posts_server.rs::safety_label_to_proto`).

---

## Cadence reminder

Long-form posts compete with each other. Don't ship two dwell posts within 6 hours — the author-diversity decay (`home-mixer/scorers/author_diversity_scorer.rs`) will halve the second one for any viewer who saw both.

## Output contract (when invoked)

When the user asks you to draft a dwell-time post, return:

1. The chosen pattern (number + name from above).
2. The drafted post (target 800-1500 chars; ≤4 short paragraphs separated by blank lines).
3. The target signal: always `dwell_score` + `dwell_time`, plus co-triggers if applicable.
4. Risk flags: any pattern-specific anti-patterns.
5. Strong-first-line check: does line 1 stop the scroll on its own, without depending on lines 2+?
