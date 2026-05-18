# Spam Classifier & Brand-Safety Avoidance

Source:
- `grox/tasks/task_spam_detection.py` — the spam detection task.
- `grox/plans/plan_spam_comment.py` — the spam plan.
- `home-mixer/models/brand_safety.rs` — `BrandSafetyVerdict` enum.
- `home-mixer/ads/util.rs::has_avoid` — `MediumRisk` triggers ad-adjacency avoidance.
- `home-mixer/candidate_hydrators/ads_brand_safety_hydrator.rs` and `ads_brand_safety_vf_hydrator.rs` — brand-safety hydration.

Spam and brand-safety classifiers act before VF labels. A spam verdict can suppress your post; a `MediumRisk` brand-safety verdict limits monetization adjacency and signals lower-quality content to downstream scoring.

---

## Spam classifier — what it catches

`grox/tasks/task_spam_detection.py` is the classifier endpoint. The plan (`plan_spam_comment.py`) is named for "spam comment" — implying primary application is on replies — but the model is broadly used.

Pattern families that pattern-match to spam:

### Repetition
- Same or near-same text posted many times in a window.
- Same image/video reused across posts.
- Reply that copies wording from many other replies.

### Engagement-bait phrasing
- "Like if you agree / retweet if you disagree."
- "Drop a 🔥 if you want me to keep posting."
- "Follow for more!"
- "Wait until you see #2."
- "You won't believe what happens next."

These triggered enough at scale that they're recognizable patterns.

### Reply-chain spam
- Mass-replying to large accounts with off-topic content to gain visibility.
- Replying to one's own posts repeatedly to push them up (`dedup_conversation_filter.rs` partially defends against this, but the spam classifier catches the pattern too).

### Link-stuffing
- Multiple shortened URLs in one post.
- URLs that resolve to known-bad domains.
- "Check out my [link]" plus minimal context.

### Mass-follow / mass-engage patterns
- Reciprocal follow rings detected via graph patterns.
- Identical engagement patterns across many accounts (engagement pods).

---

## Brand-safety verdicts

`home-mixer/models/brand_safety.rs`:

```rust
pub enum BrandSafetyVerdict {
    LowRisk,
    MediumRisk,
    // possibly others
}
```

`MediumRisk` is the "avoid for ads" verdict. From `home-mixer/ads/util.rs`:

```rust
pub(crate) fn has_avoid(post: &ScoredPost) -> bool {
    post.brand_safety_verdict() == BrandSafetyVerdict::MediumRisk
}
```

Posts with `MediumRisk`:
- Don't get ads placed adjacent.
- Are filtered out of "safe gap" placements for ads (`find_safe_gaps` in `home-mixer/ads/util.rs`).
- Signal to downstream systems that this is non-premium content.

While `MediumRisk` doesn't directly drop your post from organic For You, it suggests your content has triggered enough mid-risk signals that the system treats it cautiously.

### What earns MediumRisk

- Adult-adjacent content (without full NSFW).
- Strong language clusters.
- Political controversy without policy-violating content.
- Health / wellness claims that could be misleading.
- Crypto / financial claims that could be promotional.
- Gore-adjacent imagery (medical, accident-witness, even if not graphic).

---

## Avoidance strategy

### Don't engagement-bait

Use the recipes (`references/recipes/`) instead. Reply-bait via natural patterns (questions, contrarian takes) reads as authentic; "RT if you agree" reads as spam.

### Don't recycle content fast

`PreviouslySeenPostsFilter` already excludes already-seen posts per viewer. The spam classifier catches the pattern from the author side. If you want to re-surface a successful post, quote it with new context (`references/recipes/quote.md` Pattern 3) — that creates a new post ID with the old content embedded.

### Use links sparingly and contextually

If you link, give the reader a reason to click that's in your text, not in the link. "Wrote a thing on X" + bare link = low click intent. "Here's the part I think most people get wrong about X: [link]" = high click intent + clean.

### Avoid follow-mass / engage-mass behaviors

- Follow at most ~50 people/day (and decreasing over time as your account ages).
- Don't unfollow-refollow cycles — pattern-detected.
- Engage where you genuinely have something to add. Quality of engagement matters; quantity hurts.

### Reply only when you can add value

Reply-spam is one of the highest-signal spam patterns. Replying to every viral post with a generic "great post 🙏" — every reply added to your training signal as spam.

### Sources for any quantitative or controversial claim

Reduces both Community Note risk (`NSFA_COMMUNITY_NOTE`) and brand-safety MediumRisk verdict — both classifiers reward attributed content.

---

## What MediumRisk doesn't kill

MediumRisk is not a death sentence for organic reach. Many high-engagement creators sit in MediumRisk because of their topic (e.g., political commentators). For those:
- They earn engagement on their followers and within their topic cluster.
- They lose monetization adjacency and possibly some OON expansion.

If your strategy is organic-only (no ad revenue dependency) and you stay clear of NSFW/gore/PTOS, MediumRisk is survivable. Just expect a real ceiling on OON expansion vs. a `LowRisk` peer.

---

## Brand-safety adjacency mechanics

`home-mixer/ads/util.rs` reveals interesting interactions:

```rust
pub(crate) fn should_drop_bsr_low(ad: &AdIndexInfo, ...) -> bool {
    let risk = ad...brand_safety_risk();
    if !matches!(risk, BrandSafetyRiskLevel::BsrLow | BrandSafetyRiskLevel::BsrIas) {
        return false;
    }
    above.map(is_lr).unwrap_or(false) || below.map(is_lr).unwrap_or(false)
}
```

If an advertiser's brand-safety-risk is low (BsrLow), they ONLY want to appear adjacent to LowRisk posts. So MediumRisk posts not only don't get the ad themselves — they prevent ads from showing in adjacent slots. The system treats MediumRisk as contagious.

This isn't a direct organic-ranking penalty, but it's a signal that the broader system treats your content as constrained.

---

## Output contract (when invoked)

When the user asks about spam / brand-safety risk, return:

1. Audit of their recent posts for spam-pattern triggers.
2. Brand-safety verdict prediction (LowRisk / MediumRisk based on topical / phrasing audit).
3. Specific changes to move from MediumRisk → LowRisk if applicable.
4. The trade-off: which content trade-offs are acceptable (some niches inherently MediumRisk and that's OK).
