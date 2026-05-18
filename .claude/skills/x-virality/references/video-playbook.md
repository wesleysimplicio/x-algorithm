# Video Playbook

Target signals: `vqv_score` × VQV weight, `quoted_vqv_score` × quoted-VQV weight.
See `home-mixer/scorers/weighted_scorer.rs::vqv_weight_eligibility`, `home-mixer/scorers/ranking_scorer.rs:132-144`, `home-mixer/candidate_hydrators/video_duration_candidate_hydrator.rs`, `home-mixer/candidate_hydrators/tweet_type_metrics_hydrator.rs:82-93`.

Video has two distinct mechanics:

1. **Gating**: VQV weight is zero if your video is ≤ `MinVideoDurationMs`. A 3-second clip gets no video credit at all.
2. **Bucketing**: the model conditions on duration buckets — `VIDEO_LTE_10_SEC`, `VIDEO_BT_10_60_SEC`, `VIDEO_GT_60_SEC`. Each bucket is a separate feature; the model has learned different patterns for each.

Pick a bucket on purpose.

---

## The three buckets

### ≤10s — the loop / hook bucket

**Use for:**
- Punchline-driven content where the payoff is in seconds 1-3.
- Visual hooks designed to loop (closing matches opening).
- Reactions / memes.

**Algorithm context:** `VIDEO_LTE_10_SEC` is the bucket. To clear VQV gating, the video must be > `MinVideoDurationMs` — a reasonable working assumption is 5-6 seconds (verify against `params::MinVideoDurationMs` in your build). Anything ≤ that runs no VQV credit.

**Risk:** if you're at 3-5s, you may be sub-threshold for VQV but still in the `VIDEO_LTE_10_SEC` bucket. You get the video-presence feature but zero VQV weight. Two safe options: go to ≥7-8s, or drop the video entirely and use an image.

### 10-60s — the clip bucket

**Use for:**
- Talking-head clips, single-point explanations.
- Tutorials with one specific takeaway.
- Demos where the "wow" is visible in the first 3 seconds and the next 30-50 explain.

**Algorithm context:** `VIDEO_BT_10_60_SEC` is the bucket. This is the sweet spot for VQV — long enough to clear gating with margin, short enough that viewers actually finish. VQV is a *quality* view, so completion matters; ranking_scorer treats this as a separate predicted action.

**Risk:** burying the hook past second 3-5 — viewers don't dwell, `not_dwelled_score` rises.

### >60s — the segment bucket

**Use for:**
- Mini-essays in video form.
- Multi-part explanations.
- Conversations / interviews.

**Algorithm context:** `VIDEO_GT_60_SEC` is the bucket. Long-form video is rarer in the corpus, so it's a stronger differentiation feature, but the completion rate is lower → `not_dwelled_score` risk is higher.

**Risk:** any second past 60 that doesn't earn its keep drives `not_dwelled_score` for viewers who scroll mid-watch. Cut ruthlessly.

---

## Sub-bucket: the first 3 seconds

The first 3 seconds decide `not_dwelled_score`. The algorithm doesn't know you have a great payoff at second 45 — it learns from viewers' first 3-second behavior.

**Rules:**
1. **Lead with the strongest visual frame.** No logos, no slow fades, no "hi I'm X" — those go second 4+.
2. **Caption the hook.** Most viewers watch muted. Sound-on content needs the visual to land first.
3. **The hook is the cover.** The poster frame of the video is what shows in feed. Pick it explicitly.

---

## VQV gating — the math

From `home-mixer/scorers/weighted_scorer.rs:72-81`:

```rust
fn vqv_weight_eligibility(candidate: &PostCandidate) -> f64 {
    if candidate.video_duration_ms.is_some_and(|ms| ms > p::MIN_VIDEO_DURATION_MS) {
        p::VQV_WEIGHT
    } else {
        0.0
    }
}
```

If duration is `Some(ms)` and `ms > MinVideoDurationMs`, you get the VQV weight. Otherwise zero. Note: **strictly greater than**, not `>=`.

For quoted videos, `ranking_scorer.rs:139-144` adds an `EnableQuotedVqvDurationCheck` flag. If the flag is on (the production default per the field name), quoted videos are gated identically.

**Implication:** if you're at exactly the threshold, you fail. Add 1-2 seconds of margin.

---

## Photo-expand alternative

If your content can land as an image, ask whether it should. `photo_expand_score` is a positive weight (`weighted_scorer.rs:52`), and images don't have the gating risk videos do. An image:

- Always counts (no duration gate).
- Triggers `photo_expand_score` if the reader taps.
- Renders well in DM previews → drives `share_via_dm_score`.

Use video when the content genuinely needs motion. Otherwise prefer images.

---

## Cadence with video

Same author-diversity decay rules apply (`home-mixer/scorers/author_diversity_scorer.rs`). Two video posts within an hour fight each other for ranking slots. Space them out.

## Output contract (when invoked)

When the user asks you to draft a video post, return:

1. The chosen duration bucket and target duration.
2. The first-3-seconds plan: visual + caption hook.
3. VQV gating check: is the target duration > `MinVideoDurationMs` with margin?
4. The post text (separate from the video).
5. Risk flags: completion-rate risk, gating risk, brand-safety risk on the imagery.
