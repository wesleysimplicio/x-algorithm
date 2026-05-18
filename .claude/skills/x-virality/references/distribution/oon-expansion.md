# Out-of-Network (OON) Expansion Playbook

Source: `home-mixer/scorers/oon_scorer.rs`, `home-mixer/scorers/ranking_scorer.rs::effective_oon_weight`, `home-mixer/sources/phoenix_source.rs`, `home-mixer/sources/phoenix_moe_source.rs`, `home-mixer/sources/phoenix_topics_source.rs`.

Every post that reaches a non-follower goes through the OON scorer. From `ranking_scorer.rs`:

```rust
let final_score = match c.in_network {
    Some(false) => after_diversity * effective_oon,
    _ => after_diversity,
};
```

`effective_oon_weight` returns one of three values:
- `TopicOonWeightFactor` if the request is topic-filtered.
- `NEW_USER_OON_WEIGHT_FACTOR` if the viewer is a new user (account age < `NewUserAgeThresholdSecs`, with at least `NEW_USER_MIN_FOLLOWING` follows).
- `OonWeightFactor` otherwise.

All three are < 1.0 in practice — OON candidates are always penalized. Your ceiling for organic reach beyond your followers is bounded by this factor. Escaping the bound is what "going viral" looks like.

---

## The math of escape

If `OonWeightFactor = 0.5` and your weighted score for an in-network viewer is 1.0, the same predicted engagement on an OON viewer scores 0.5. To beat an in-network competitor at 0.7, your OON-side raw weighted score has to be > 1.4 — roughly 2x.

So OON virality requires posts that score ~2x better than typical in-network content. The only paths there:

1. Posts that hit multiple positive weights simultaneously (reply + dwell + share at once).
2. Posts that maximize the strongest weight (`follow_author_score`).
3. Posts that minimize predicted negatives (`not_interested_score`, `block_author_score`, `mute_author_score`).

---

## Strategy 1 — Multi-signal stacking

Design posts that predict well on multiple actions, not just one. A post that's strong on reply only might score 0.3 weighted. A post strong on reply + dwell + share scores 0.6+. That's where the OON penalty becomes survivable.

**How to stack:**
- Reply-bait (`references/recipes/reply-bait.md`) + visual evidence (image) → reply + photo_expand + dwell.
- Dwell long-form (`references/recipes/dwell.md`) + quotable one-liner inside → dwell + share + quote.
- Series marker (`references/recipes/follow-magnet.md`) + useful list → follow + share via copy-link.

---

## Strategy 2 — Maximize follow_author_score

`follow_author_score` is the heaviest positive weight. A post that drives a follow scores more than several posts that drive likes. Plus — once they follow, future posts skip the OON penalty for that viewer entirely.

This is asymmetric leverage. Optimize for follows over any other single metric on OON content.

---

## Strategy 3 — Minimize predicted negatives

The negative weights (`not_interested`, `block_author`, `mute_author`, `report`, `not_dwelled`) are large. Phoenix predicts these *before* the post is shown, based on similarity to historical not-interested content.

**To minimize:**
- Don't use rage-bait phrasing — pattern matches to mute/block training data.
- Don't include muted-keyword candidates (common spam terms — see `home-mixer/filters/muted_keyword_filter.rs`).
- Strong first line — `not_dwelled_score` predicts on the post's stop-scroll quality.
- Civil framing on contrarian takes — disagreement is fine, attack is punished.

---

## Strategy 4 — Pick the right product surface

`scored_posts_server.rs::log_request_info` distinguishes:
- `for_you` — full Phoenix OON
- `ranked_following` — in-network only
- `topics` — topic-filtered, uses `TopicOonWeightFactor`
- `for_you_with_snoozed_topics` — excluding certain topics

If you tag your post with a strong topic signal (Grox classifies it via `home-mixer/candidate_hydrators/filtered_topics_hydrator.rs`), it becomes a candidate in topic-filtered feeds with `TopicOonWeightFactor`. The topic OON factor is often more forgiving than the global one because the audience self-selected by topic.

**Implication:** post content that classifies cleanly into a topic (clear keywords, focused subject) gets a topic-feed second life that generic posts don't.

---

## Strategy 5 — Stop targeting topics your audience has snoozed

If users have snoozed your usual topic, you fall into `for_you_with_snoozed_topics` — restricted product surface. To re-enter the main feed, occasionally post outside the snoozed topic to widen your topic classification.

---

## The Phoenix MoE and topics paths

The candidate set isn't just `phoenix_source` (general retrieval) — it also pulls from:
- `phoenix_moe_source.rs` — Mixture-of-Experts variant for more specialized retrieval.
- `phoenix_topics_source.rs` — retrieval scoped to topics.

Posts that retrieve well in topic source are double-counted as candidates. If your post's multimodal embedding (`grox/embedder/multimodal_post_embedder_v5.py`) classifies into a topic strongly, you appear in both general OON retrieval AND topic-filtered retrieval. Two candidate slots for one post.

---

## Anti-strategy: chasing OON before in-network is solid

If your in-network engagement rate is low, OON penalty bites doubly — Phoenix sees followers don't engage, predicts other viewers won't either, scores low. **Build in-network engagement first** (post to your followers, earn replies/dwell/follows from existing audience), then OON virality is achievable.

## Output contract (when invoked)

When the user asks about reaching beyond their followers, return:

1. Current in-network engagement audit (their hit rate on followers — proxy: replies/follower count).
2. Which multi-signal stacking pattern fits their content.
3. Topic-classification check: does their post classify cleanly?
4. Predicted-negative audit: any phrasings that risk mute/block/report training-data similarity.
5. A 30-day expansion plan: in-network depth → topic-feed entry → general OON.
