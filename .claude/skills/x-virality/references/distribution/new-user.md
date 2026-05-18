# New-User Playbook

Source: `home-mixer/scorers/ranking_scorer.rs::effective_oon_weight` (lines 220-239), `home-mixer/query_hydrators/user_features_query_hydrator.rs`.

```rust
let is_eligible_new_user = duration_since_creation_opt(query.user_id)
    .map(|age| age < new_user_age_threshold)
    .unwrap_or(false)
    && query.user_features.followed_user_ids.len() >= NEW_USER_MIN_FOLLOWING;

if is_eligible_new_user {
    NEW_USER_OON_WEIGHT_FACTOR
} else {
    oon_weight_factor
}
```

A new account that follows enough accounts (`NEW_USER_MIN_FOLLOWING`) within the new-user window (`NewUserAgeThresholdSecs`) gets `NEW_USER_OON_WEIGHT_FACTOR` instead of the regular `OonWeightFactor`.

This is a one-time, time-limited window. The new-user OON factor is more forgiving — meaning OON posts the new user *receives* are penalized less. Translated: as a new account, you also benefit on the production side because OON content is more visible to you, which feeds back into your engagement history.

But the more important application of this knowledge is for the author side: **the first 30 days of a new account are the easiest time to grow.**

---

## Why the first 30 days matter

1. **Lower follower bucket** — `tweet_type_metrics_hydrator.rs:56-76` exposes follower buckets to the model (0-100, 100-1K, ...). New accounts start in 0-100, and the model has learned different ranking patterns for small accounts. Often: small-account posts ride differently in OON retrieval because the model treats them as a separate feature space.

2. **Empty engagement history → cold start** — Phoenix's user-tower input (`phoenix/recsys_retrieval_model.py`) needs engagement signals to embed the user. Until enough actions accumulate, the model has weaker priors against amplifying your content.

3. **New-account flag** — if X tracks newness as a feature (signals in `tweet_type_metrics_hydrator.rs` reference `EMPTY_REQUEST`, `NEAR_EMPTY` for session newness; account-age newness is signaled via `is_eligible_new_user`), there's a specific code path.

4. **Cross-bucket movement** — every follower bucket you cross (0→100, 100→1K, etc.) re-anchors how the model ranks you. The first crossings are the fastest.

---

## Strategy 1 — Lock in 100 follows fast

Crossing from `AUTHOR_FOLLOWERS_0_100` to `AUTHOR_FOLLOWERS_100_1K` is the first bucket jump (`tweet_type_metrics_hydrator.rs:56-65`). The model treats posts from the new bucket differently — typically more amplifiable.

**Concrete:**
- Use the follow-magnet recipes (`references/recipes/follow-magnet.md`) heavily in week 1-2.
- Post identity-declaring content (Pattern 1 in `references/recipes/follow-magnet.md`) — readers need to know what they're signing up for.
- Engage with 20-50 cluster-central accounts (per `references/distribution/mutual-follow.md`) — each mutual follow lifts your Jaccard and exposes you to their followers.

---

## Strategy 2 — Avoid the cold-start trap

The Phoenix user-tower embedding is built from engagement history. As a new user, you have none. Until you build it:
- Your own feed is generic (cold-start recommendations).
- Phoenix can't strongly predict who would like your posts because the system has limited data on you.

**Concrete:** spend the first week consuming + engaging deliberately. Like and reply to content in your target niche. Each engagement updates your user-tower input. By week 2, Phoenix has a clearer picture of where you fit.

This also helps the *recommendation* side: viewers in your niche start seeing your content because your engagement footprint is unambiguous.

---

## Strategy 3 — Use the new-user OON loophole BEFORE it closes

The window is `NewUserAgeThresholdSecs` from account creation. After that, you snap to the regular `OonWeightFactor`. Treat the new-user window as borrowed reach — use it to acquire followers who will then carry you into the regular regime.

**Concrete:**
- Post at least 1x/day during the new-user window.
- Each post should aim to convert OON impressions into follows (follow-magnet patterns).
- Don't waste new-user impressions on low-effort posts that earn likes but no follows.

---

## Strategy 4 — Build the mutual-follow cluster early

`mutual_follow_jaccard_hydrator.rs` is feature-bound on viewers having at least 256 MinHash slots. As a new account, you start with very little. Each mutual you build adds signal. By the end of the new-user window, you want at least 10-20 niche-central mutuals so Phoenix has cluster signal to score your posts against viewers in that cluster.

---

## Strategy 5 — Don't expect old posts to resurface

`home-mixer/filters/age_filter.rs` drops posts older than `max_age`. As a new account, you don't have a backlog the algorithm rediscovers. Each post is one shot. Plan your first 30 posts deliberately.

---

## Anti-patterns specific to new accounts

1. **Mass-following everyone** — pattern-matches to spam (`grox/tasks/task_spam_detection.py`).
2. **Posting before establishing identity** — first 5 posts shape what readers expect. If they're inconsistent, follow conversion is low.
3. **Engagement-baiting** — new accounts get scrutinized more aggressively by the spam classifier; engagement-bait patterns are detected.
4. **Buying followers** — bot-cluster MinHash patterns get caught; even if they don't, they pollute your Jaccard with viewers in your niche.

## Output contract (when invoked)

When the user asks about growing a new account, return:

1. Current account age + follower count → which window they're in (new-user OON eligible? bucketed where?).
2. Identity declaration: what's the one-line "what you'll get if you follow."
3. First 10 mutuals to build (niche-central accounts).
4. Posting cadence for the first 30 days.
5. Risk flags: spam classifier triggers, follow-mass patterns to avoid.
