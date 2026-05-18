# Thread Structure Playbook

Threads are the longest-form X format. They unlock dwell time, multiple share entry points, and reply-bait at every link. They also hit two specific algorithm quirks: the conversation dedup filter and the in-network reply hydrator.

See:
- `home-mixer/filters/dedup_conversation_filter.rs` — collapses multiple branches of the same conversation. Threads are linear, so this rarely hurts threads themselves, but it shapes how reply-trees fan out.
- `home-mixer/candidate_hydrators/following_replied_users_hydrator.rs` — surfaces threads where the author has replied to people the viewer follows. Replying to early commenters in your thread compounds reach.
- `home-mixer/scorers/ranking_scorer.rs` — every tweet in the thread is scored independently. Each one fights the author-diversity decay for the same author.

---

## Pattern 1 — Tweet 1 carries the whole thread alone

**Mechanic:** the first tweet of the thread is a complete post. The thread is optional reading for people who want more.

**Template:**

> [Tweet 1 — strong, standalone, ≤280 chars. Carries the full claim.]
>
> [Tweet 2 — first piece of evidence / detail.]
> [Tweet 3 — second piece.]
> [Tweet 4 — counterargument, edge case, nuance.]
> [Tweet 5 — payoff / synthesis.]

**Why this works:** Tweet 1 has to land alone because most viewers won't expand. It fights for `reply_score` / `share_score` on its own. Tweet 2-N earn `dwell_time` from readers who do expand. Author-diversity decay (`home-mixer/scorers/author_diversity_scorer.rs::multiplier`) penalizes Tweets 2-N within a single feed render, but expanded-thread reads happen on the post page where the decay doesn't apply.

**Anti-patterns:**
- Tweet 1 says "thread 👇" without content — reads as engagement-bait, hits `grox/tasks/task_spam_detection.py`.
- Tweet 1 ends mid-sentence — reader needs to expand to make sense of it; most won't, and `not_dwelled_score` fires on the first tweet.

---

## Pattern 2 — Each tweet is independently shareable

**Mechanic:** every tweet in the thread could stand alone as a single post.

**Template:**

> [Tweet 1: complete idea.]
> [Tweet 2: complete idea.]
> [Tweet 3: complete idea.]
> [...]

**Why this works:** any tweet in the thread can earn `share_via_dm_score`, `share_via_copy_link_score`, or `quote_score` independently. Readers screenshot the one tweet that resonated with them. Maximizes share surface area.

**Anti-patterns:**
- "1/12" style with each tweet being a fragment — only Tweet 1 is shareable.
- Long chains (>10 tweets) — diminishing returns; viewers exit at tweet 4-5.

---

## Pattern 3 — Build-up to a payoff

**Mechanic:** thread structured as a narrative — setup, complication, resolution.

**Template:**

> [Tweet 1 — hook: name the tension.]
> [Tweet 2-3 — setup / context.]
> [Tweet 4-5 — complication / "and then this happened".]
> [Tweet 6 — payoff / lesson.]

**Why this works:** readers expand because the hook promises a story. Once they're in, they read through for the payoff — driving `dwell_time` linearly. The payoff tweet often earns the most shares because it's the resolution worth retelling.

**Anti-patterns:**
- Payoff that doesn't pay off — readers feel cheated, lower `dwell_score` on future threads from you.
- Thread that buries the payoff after too many setup tweets — readers exit before the payoff.

---

## Pattern 4 — Numbered breakdown across N tweets

**Mechanic:** the thread is a numbered list, with one tweet per item.

**Template:**

> [Tweet 1: "N things about X:"]
> [Tweet 2: "1. ..."]
> [Tweet 3: "2. ..."]
> [...]
> [Tweet N+1: "Bonus: ..."]

**Why this works:** structured, predictable rhythm. Readers expand the thread expecting a list and stay through because each tweet is a discrete unit. Good for accumulating `dwell_score` across many tweets.

**Anti-patterns:**
- More than 10 items — return on dwell diminishes; viewers exit.
- Items that overlap — feels like padding, kills credibility.

---

## Replying to your own thread

You CAN'T multiply slots by reply-spamming your own thread. `home-mixer/filters/dedup_conversation_filter.rs` collapses multiple branches of the same conversation in the For You feed — only one branch survives per viewer. Strategy:

1. **Post the whole thread together.** Don't drip-feed.
2. **Reply to early commenters, not yourself.** Each reply to a real commenter hits `following_replied_users_hydrator.rs` for any viewer who follows that commenter — strong distribution boost. Replies to yourself don't.
3. **Quote-amplify the strongest tweet later.** When one tweet in the thread takes off, quote it as a new post with fresh context. The quote is a new post ID, escaping the conversation dedup.

## In-network reply boost

`home-mixer/candidate_hydrators/following_replied_users_hydrator.rs` exposes which posts in the candidate set are from authors who recently replied to someone the viewer follows. If you reply to early commenters in your thread, your thread becomes a recommendation candidate for everyone who follows those commenters. This is the second-order distribution loop unique to threads — bare posts don't have it.

## Output contract (when invoked)

When the user asks you to draft a thread, return:

1. The chosen pattern (number + name).
2. The thread, numbered, each tweet ≤280 chars.
3. The standalone-Tweet-1 check: does Tweet 1 work alone?
4. Per-tweet target signal: which signal each tweet is optimized for.
5. First-60-minute plan: which early commenters to engage with, and how (real replies > self-replies because of the in-network reply hydrator).
