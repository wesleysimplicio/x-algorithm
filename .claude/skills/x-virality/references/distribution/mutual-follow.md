# Mutual-Follow Jaccard Strategy

Source: `home-mixer/candidate_hydrators/mutual_follow_jaccard_hydrator.rs`, `home-mixer/query_hydrators/mutual_follow_query_hydrator.rs`.

For each candidate post, the algorithm computes Jaccard similarity between the viewer's follower MinHash and the candidate author's follower MinHash. Higher Jaccard means the author and viewer are inside the same social cluster.

This is a feature the Phoenix transformer uses; it doesn't appear as a direct multiplier in `weighted_scorer.rs`, but it shifts the *predicted* per-action probabilities upward when high (authors inside the viewer's cluster get higher predicted engagement).

---

## How MinHash + Jaccard works here

From `mutual_follow_jaccard_hydrator.rs`:

```rust
fn jaccard_from_minhash(a: &[i64], b: &[i64]) -> f64 {
    let len = a.len().min(b.len());
    if len == 0 { return 0.0; }
    let matching = a.iter().zip(b.iter()).filter(|(x, y)| x == y).count();
    matching as f64 / len as f64
}
```

MinHash signatures are at least 256 hashes long (`MIN_HASHES`). The Jaccard estimate is the fraction of matching hash slots. For two authors with very overlapping follower sets, many hash slots match; for disjoint sets, almost none.

The viewer's MinHash (`query.viewer_minhash`) is computed from their follower graph. Your MinHash, as an author, is fetched per candidate via `strato_client.batch_get_minhash_with_count`.

---

## What this means for distribution

A post from author A retrieved as an OON candidate for viewer V is scored more favorably by Phoenix when `jaccard(V's follower MinHash, A's follower MinHash)` is high. So:

1. Building a dense mutual-follow cluster in your niche lifts every post you make for everyone *inside* that cluster.
2. Authors outside your cluster pull less weight when retrieved into your audience's feeds.
3. Cross-cluster bridges (you follow someone with a different but overlapping cluster) extend your reach.

---

## Strategy 1 — Follow the dense center of your niche

The 50-200 most-active accounts in your specific niche form a dense follower-graph subset. Following them, and getting them to follow back, raises your MinHash overlap with everyone in their followers.

**Concrete:** identify the 20 highest-leverage accounts in your niche. Follow them. Engage genuinely (real replies > follows that get unreciprocated). Aim for mutual follows — those are what shift your MinHash.

**Why this works:** every mutual follow with a niche-central account adds N viewers (their followers) where your Jaccard is now higher. Phoenix predictions for those viewers rise.

**Anti-pattern:** follow-spam. The author-socialgraph filter (`home-mixer/filters/author_socialgraph_filter.rs`) excludes blocked / muted authors. Mass-follow patterns also pattern-match to spam (`grox/tasks/task_spam_detection.py`).

---

## Strategy 2 — Be replied-to by mutuals

`home-mixer/candidate_hydrators/following_replied_users_hydrator.rs` exposes "this author has replied to people the viewer follows." Posts with this flag get a distribution boost to anyone who follows the replied-to user.

**Concrete:** post things that mutuals in your cluster will reply to. Each reply from them, if it lands in a feed of someone who follows them, exposes you. That exposure is one of the most cost-effective expansion paths because it requires no follow on your end.

**Anti-pattern:** baiting unrelated mutuals to reply (off-topic tags / quotes) — drives `not_interested_score` on the mutual's audience.

---

## Strategy 3 — Cross-cluster bridges

If your only mutuals are in cluster A, your retrieval is bounded by cluster A. Adding a small number of mutuals in cluster B that's adjacent — not random, but topically related — extends your Jaccard reach into cluster B.

**Concrete:** if you're a Rust dev (cluster A: systems programmers), build a few mutuals with database-systems folks (cluster B: data infra). Your posts about Rust now retrieve marginally better to data-infra viewers.

**Anti-pattern:** chasing unrelated clusters for raw follower count. The retrieval boost only happens for clusters where your content is plausibly relevant. Otherwise you get retrieved + scrolled past → `not_dwelled_score` accumulates.

---

## Strategy 4 — Quote-amplify within your cluster

When a mutual posts something quotable, quote-post with your own take. `quote_score` + `quoted_click_score` fire for you. Your audience sees the mutual; their audience sees you. Reciprocal cross-pollination raises both sides' Jaccard with the shared overlap.

**Concrete:** in your niche, quote at least one mutual per week with substantive added context. Bare reposts don't trigger the same signal cascade (only `retweet_score`, vs `quote_score` + `quoted_click_score` + potentially `quoted_vqv_score`).

---

## Tracking signal: how to tell if your mutual graph is working

Indirect signals (X doesn't expose Jaccard directly):

1. **OON impressions on your posts** rising — your retrieval reach is expanding.
2. **Replies from second-degree connections** (followers of your mutuals you don't follow) — the mutual reply hydrator is firing.
3. **Follow conversion rate on niche posts** rising — posts that hit the niche cluster densely earn follows more efficiently.

If none of these is moving over weeks, the mutual graph isn't dense enough. Add more genuine engagement with cluster-central accounts.

---

## What NOT to do

- **Buy followers** — bot follower sets have predictable MinHash patterns the spam classifier (`grox/tasks/task_spam_detection.py`) can pick up.
- **Follow-for-follow with random accounts** — Jaccard depends on *who* the mutuals are, not raw count. 100 random mutuals < 10 niche-central mutuals.
- **Engagement pods** — coordinated reciprocal engagement is a spam pattern.

## Output contract (when invoked)

When the user asks about distribution or follower-graph strategy, return:

1. Their current niche / cluster diagnosis (what you can infer from their recent posts).
2. The cluster-central accounts you'd recommend mutual-follow with.
3. Specific quote-amplification targets in their niche.
4. A 2-week measurement plan: which indirect signals to watch.
