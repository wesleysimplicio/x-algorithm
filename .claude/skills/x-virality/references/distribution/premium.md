# X Premium / Subscription Playbook

Source: `home-mixer/candidate_hydrators/subscription_hydrator.rs`, `home-mixer/query_hydrators/subscribed_user_ids_query_hydrator.rs`, `home-mixer/filters/ineligible_subscription_filter.rs`, `home-mixer/candidate_hydrators/tweet_type_metrics_hydrator.rs:37-40` (`SUBSCRIPTION_POST` bitset bit).

X tracks subscription status per post (the post's author has Premium / a subscription tier) and per viewer (the viewer is a subscriber, possibly to specific authors). This shows up in three places:

1. `SubscriptionHydrator` populates `candidate.subscription_author_id` with the author's subscription tier id.
2. The Phoenix model conditions on `SUBSCRIPTION_POST` as a tweet-type feature.
3. `IneligibleSubscriptionFilter` removes paywalled-tier content from viewers without access.

---

## What the model sees

`tweet_type_metrics_hydrator.rs:37-40`:

```rust
if candidate.subscription_author_id.is_some() {
    true_tweet_types.insert(SUBSCRIPTION_POST);
}
```

Posts where the author has any subscription tier flip the `SUBSCRIPTION_POST` bit in the candidate's tweet-type bitset. The Phoenix transformer treats this as a feature. Whether it's a positive boost is an empirical question (depends on training data + runtime params), but the existence of the feature means subscription posts ride a different ranking path than non-subscription posts.

---

## Strategy 1 — Subscribe to differentiate

If you're an active poster with engaged audience, X Premium adds the `SUBSCRIPTION_POST` flag to all your posts. That flag is a distinct feature the model has learned patterns for. At minimum, it changes how your posts are scored vs identical non-subscription posts.

It also unlocks longer-form posting limits (longer tweets, longer videos), which expands the formats you can use — particularly `dwell_score` long-form (`references/recipes/dwell.md`) and the >60s video bucket (`references/video-playbook.md`).

**Trade-off:** subscription content may be gated for viewers without Premium via `IneligibleSubscriptionFilter` (`home-mixer/filters/ineligible_subscription_filter.rs`). If you ONLY post Premium-tier content, you lose reach to non-subscribers entirely. Mix free-tier posts with Premium-tier content.

---

## Strategy 2 — Don't paywall everything

`IneligibleSubscriptionFilter::filter`:

```
Removes paywalled content user can't access.
```

If your typical viewer is not a subscriber to your tier, they never see your paywalled posts. For organic reach: keep the majority of your posts at the free tier so they're eligible for everyone's For You feed.

Reserve Premium-only posts for:
- Deep dives where the audience is already paying.
- Exclusive content that justifies the paywall.
- Comment-only content that wouldn't have wide reach anyway.

---

## Strategy 3 — Use the longer-character limit deliberately

Premium unlocks 25,000-character posts. Use that for:
- Mini-essays that would otherwise be a thread (single post = single ranking slot, no author-diversity decay across multiple tweets).
- Code blocks / data dumps that read better in one continuous block.
- Annotated documents.

**Important caveat:** longer posts have lower stop-scroll rates per character. A 5,000-char post needs the first 100 chars to land before readers expand. Apply the dwell-recipe first-line discipline (`references/recipes/dwell.md` Pattern 1).

---

## Strategy 4 — Pin a Premium-tier preview

If you're using Premium for the longer format, pin a representative example to your profile. Profile clicks (`profile_click_score`) are a positive weight; readers who click through and see a substantive long-form post are more likely to follow than readers who see only short replies.

---

## What we don't claim

- **Subscription is not a guaranteed ranking boost.** The flag exists in the feature set; whether it scores positively depends on runtime weights + training data. Treat it as a category-changer (different ranking path), not as a multiplier.
- **No "verification = amplification".** The codebase distinguishes subscription tier IDs and verification status (`gizmoduck_hydrator.rs`), but neither shows up as a direct weight in `weighted_scorer.rs` / `ranking_scorer.rs`. They are model features, not multipliers.

---

## Anti-patterns

- **Paywalling everything.** Kills reach to the majority audience.
- **Engagement-baiting subscribe** ("subscribe for more!") — pattern-matches to spam.
- **Premium-only on follow-magnet content.** The whole point of follow-magnets is conversion; gating them defeats the purpose.

## Output contract (when invoked)

When the user asks about Premium / subscription strategy, return:

1. Diagnosis: is their current post mix Premium-heavy or balanced?
2. Recommended mix (e.g., 80% free / 20% Premium for organic growth).
3. Which of their post types benefit most from longer character limits.
4. Risk: filter exclusion via `IneligibleSubscriptionFilter`.
