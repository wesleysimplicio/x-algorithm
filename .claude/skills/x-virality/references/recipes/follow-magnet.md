# Follow-Magnet Recipes

Target signal: `follow_author_score`.
See `home-mixer/scorers/ranking_scorer.rs` (`FollowAuthorWeight`).

This is the highest-leverage signal in the formula. A follow doesn't just count as one positive engagement — it moves the viewer from out-of-network (OON, downweighted by `OonWeightFactor < 1`) to in-network (full weight, plus served via `home-mixer/sources/thunder_source.rs`) for every future post you make. It also raises your mutual-follow Jaccard with the viewer's other follows (`home-mixer/candidate_hydrators/mutual_follow_jaccard_hydrator.rs`).

The compounding effect: one follow earned today is worth more than 100 likes, because likes don't propagate the OON penalty removal.

---

## Pattern 1 — Identity declaration in line 1

**Mechanic:** the first line tells the reader exactly who you are and why following you is a specific commitment, not a generic favor.

**Template:**

> [Role + niche + one specific commitment.]
>
> [The post content that demonstrates the commitment.]

**Example shape:**

> I write threads about [niche] every Tuesday. Today: [topic].
>
> [The actual content.]

**Why this works:** the reader gets a concrete promise — "if I follow, I get X." The model also picks up on author-followers buckets (`home-mixer/candidate_hydrators/tweet_type_metrics_hydrator.rs:56-76`), so identity-clear posts that earn follows push you toward the next follower bucket (100→1K, 1K→10K, etc.), which changes how Phoenix scores all your future posts.

**Anti-patterns:**
- "Follow for more" without a specific promise — reads as engagement-bait and pattern-matches to the spam classifier (`grox/tasks/task_spam_detection.py`).
- Bio-dump in the post body — readers ignore it.

---

## Pattern 2 — Series marker

**Mechanic:** post that is explicitly part of a recurring series. Following = subscribing.

**Template:**

> [Series name] #[N]: [Topic.]
>
> [Content.]
>
> ([Frequency reminder, e.g. "every Friday".])

**Why this works:** signals "more like this, on a schedule" — drives `follow_author_score` because the reader knows what they're signing up for. Also drives `profile_click_score` as readers click through to see previous entries, and `profile_click_score` is itself a positive weight (`weighted_scorer.rs:54`).

**Anti-patterns:**
- Series that doesn't actually run — followers churn back to OON.
- Posting #1 of a new series too often — dilutes the brand of any single series.

---

## Pattern 3 — Hard-won lesson with credentials baked in

**Mechanic:** share a specific learning that implicitly proves you've done the thing.

**Template:**

> After [N years / instances] of [specific activity], here's what I wish I had known on day one: [the lesson, 3-5 lines.]

**Why this works:** the credential and the lesson arrive together. Reader thinks "I want more of what they've learned" → follow. Hits `follow_author_score` and `dwell_score` (long-form earns the dwell weight).

**Anti-patterns:**
- Vague credential ("years of experience") — no proof signal.
- Lesson that's a cliché ("be kind to your team") — kills the credibility built by the credential.

---

## Pattern 4 — Niche-cluster magnet

**Mechanic:** post something that only people deep in your specific niche will fully appreciate. Outsiders skip; insiders follow because you're rare.

**Template:**

> [Niche-specific reference / joke / observation that requires field knowledge to parse.]

**Why this works:** filters self-selectingly to your target. Your MinHash (`mutual_follow_jaccard_hydrator.rs`) gets denser in the niche cluster, which raises your Jaccard with future viewers in that cluster. Compounding network effect — the niche-clustered follows lift all your future posts inside that cluster.

**Anti-patterns:**
- Too obscure — even insiders can't parse, no engagement.
- Looks like a typo or in-joke gone wrong — readers bail thinking the post is broken.

---

## Pattern 5 — Public commitment / "I'm building [X] in public"

**Mechanic:** announce a thing you're working on. The reader follows to watch the story unfold.

**Template:**

> I'm building [specific thing]. Here's where I am at [time-stamp]: [concrete status, 2-3 lines.]
>
> Following along will show you [what the reader gets out of following].

**Why this works:** turns following into a narrative subscription. Hits `follow_author_score` and creates a natural rhythm for future `dwell_score` (status updates) and `quote_score` (people quote-amplify with their own takes).

**Anti-patterns:**
- Vague project ("I'm working on something cool") — no narrative hook.
- Never updating — followers churn, raising `not_dwelled_score` on your future posts.

---

## The OON-removal multiplier

Every follow you earn removes the `OonWeightFactor` penalty for that viewer for all future posts (`home-mixer/scorers/oon_scorer.rs`, `home-mixer/scorers/ranking_scorer.rs::effective_oon_weight`). At a typical `OonWeightFactor < 1`, this is a 1.5-3x boost on every future ranking against that viewer.

If you have to choose between optimizing for 100 likes or 10 follows on a given post, optimize for the follows. The likes pay once; the follows compound.

## New-user OON loophole

`ranking_scorer.rs:227-238`: a new user (account age below `NewUserAgeThresholdSecs`, with at least `NEW_USER_MIN_FOLLOWING`) gets `NEW_USER_OON_WEIGHT_FACTOR` instead of the regular factor. The new-user OON factor is more forgiving. For new accounts: optimize aggressively for follows in the first 30 days while the OON penalty is reduced.

## Output contract (when invoked)

When the user asks you to draft a follow-magnet post, return:

1. The chosen pattern.
2. The drafted post.
3. The implicit promise (what the reader is signing up for by following).
4. Niche-cluster awareness: which mutual-follow neighborhood you're targeting.
5. Cadence: what the follow-up posts that justify the follow look like.
