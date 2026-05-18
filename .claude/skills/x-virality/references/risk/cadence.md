# Cadence & Author-Diversity Decay

Source: `home-mixer/scorers/author_diversity_scorer.rs`, `home-mixer/scorers/ranking_scorer.rs::apply_author_diversity` (lines 186-217), `home-mixer/scorers/ranking_scorer.rs::diversity_multiplier`.

Within a single feed render, the algorithm penalizes the same author appearing multiple times. The penalty is multiplicative and compounds with position.

```rust
fn diversity_multiplier(decay_factor: f64, floor: f64, position: usize) -> f64 {
    (1.0 - floor) * decay_factor.powf(position as f64) + floor
}
```

Where `position` is the rank order of your post within the candidate set among posts from the same author. Position 0 is your highest-scored post in that batch: multiplier = 1.0. Position 1 is your second: multiplier = `(1-floor)·decay + floor`. Position 2: `(1-floor)·decay² + floor`. Etc.

---

## The numbers

Default params from the scoring docs use illustrative values like `decay=0.7`, `floor=0.3`. Actual runtime values vary, but the shape is fixed:

| Position | Multiplier (decay=0.7, floor=0.3) |
|---:|---:|
| 0 | 1.000 |
| 1 | 0.790 |
| 2 | 0.643 |
| 3 | 0.540 |
| 4 | 0.468 |
| 5 | 0.418 |
| 6 | 0.383 |
| ∞ | 0.300 (asymptotic floor) |

The 2nd post from the same author in the same render loses ~20% of its weighted score. The 3rd loses ~35%. The 4th loses ~45%.

---

## What this means in practice

The decay applies within a *single feed render* — meaning when a viewer pulls For You at a single moment. If you post 5 tweets in 10 minutes, all five enter the same candidate set for any viewer who refreshes during that window. The model sorts them by weighted score and applies the decay in that sort order.

The implication: rapid-fire posting means your posts compete *against each other* for the same viewer's slots, not against other authors' posts.

If your highest-scoring post in the batch is at multiplier 1.0 and your weakest is at 0.418, the weak one is fighting an uphill battle. A competitor's post at the weak one's raw score has multiplier 1.0 too — it wins.

---

## Strategy 1 — Space your posts

For a given viewer's typical For You session length (~10-30 minutes), aim for one post per session. If you post once an hour, the previous post is more likely to have aged out of recent-recency or been served already, and the decay doesn't bite.

**Concrete:**
- Casual cadence: 1-2 posts per day → almost never hit decay.
- Active cadence: 3-5 posts per day, spaced 4-6 hours apart → minimal decay.
- High-volume cadence: more frequent → expect decay on the 2nd+ posts per viewer session.

Don't post 5 things back-to-back in 30 minutes. Even if each is good, the system makes them compete.

---

## Strategy 2 — Mix formats

The decay is by author, not by format. But viewers' eye-tracking — and Phoenix's `not_dwelled_score` prediction — may be sensitive to format repetition (same shape, same hook style). Mix:

- Text only, then video, then image, then thread.
- Reply-bait, then dwell long-form, then share-list.

This doesn't dodge author-diversity decay technically — but it minimizes the "tuning out" reaction that drives `not_dwelled_score`.

---

## Strategy 3 — Post when your audience is active

Posting at 3 AM when nobody's online means your post sits in the candidate pool, decaying via the age filter (`home-mixer/filters/age_filter.rs`), without earning early engagement. Phoenix's first-hour ranking uses early engagement signal as input — no engagement, no ranking lift.

Post when your audience is awake. For most audiences that's a few peak windows per day; identify yours from your existing engagement patterns.

---

## Strategy 4 — Threads as a single ranking unit

Threads are multiple tweets, but viewers expand the thread on the post page, not in feed. Tweets 2-N in a thread are NOT subject to author-diversity decay in the same way as separate posts because they don't enter the candidate set as separate For-You candidates — they're rendered as a continuation.

**Implication:** if you have 5 ideas, a thread is better than 5 separate posts. A thread is one post for ranking-set purposes; 5 separate posts trigger the decay.

(Caveat: some thread starters do get re-served as standalone candidates. The first tweet of the thread is the candidate; the rest is expanded on click.)

---

## Strategy 5 — Quote-amplify instead of repost-yourself

If a recent post of yours is taking off and you want to push it further, don't re-post the same content (`PreviouslySeenPostsFilter` blocks it anyway, and the spam classifier may catch repetition). Quote the post with new context (`references/recipes/quote.md` Pattern 3). The quote is a NEW post ID — but in candidate sets where the original is also present, the decay still applies because the quote points to your own author.

**Better:** wait long enough that the original is no longer a candidate, then quote.

---

## When you DO want to post fast

Some scenarios warrant rapid-fire:

1. **Live event coverage.** Posting reactions to a live event accepts that posts 2-N decay but maximizes coverage. The first post still has full weight; the others ride at floor.
2. **Thread expansion via replies.** Following up on engaged replies in real time. These are replies, not new top-level posts — different decay path.
3. **Quote-storm of a controversy.** When everyone's commenting, your quotes need to be in the conversation window. Decay is fine; relevance > weight.

For everything else: space your posts.

---

## How to verify

You can't observe the multiplier directly. Indirect signals:

- Your post #N gets noticeably fewer impressions than #1 of the same day — decay biting.
- Engagement rate per impression is similar across the day — decay biting evenly.
- One post in a burst dramatically over-performs the rest — that one held the position-0 slot.

---

## Output contract (when invoked)

When the user asks about cadence / posting schedule, return:

1. Recommended posts/day based on their content depth.
2. Spacing rule (≥X hours between posts).
3. Calendar of when their audience is most active.
4. Format mix recommendation.
5. Risk audit: are they currently posting in bursts that trigger decay?
