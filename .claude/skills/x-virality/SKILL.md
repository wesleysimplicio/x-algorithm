---
name: x-virality
description: Use when the user asks to draft, rewrite, or optimize content for X (Twitter) — single posts, threads, replies, quote posts, or videos — and wants the work tuned to the X "For You" ranking algorithm. Triggers on requests like "make this go viral on X", "post for X algorithm", "optimize tweet", "X engagement", "viralizar no X". Applies the public X For You source code (this repo) to guide drafts toward signals the algorithm rewards (replies, dwell, shares, follows, qualified video views) and away from signals that suppress reach (not-interested, mute, block, report, VF labels, age decay, author-diversity decay).
---

# X Virality Skill

You are helping the user write content for X (Twitter) that the For You algorithm — implemented in this repository — is most likely to amplify. The repo is the source of truth for every claim in this skill. When you reference an algorithm behavior, cite the file/line in `home-mixer/`, `phoenix/`, `thunder/`, `grox/`, or `candidate-pipeline/`.

## What X actually ranks on

The final score for a post in a viewer's feed is a Phoenix transformer prediction over many actions, combined into one weighted score, then adjusted by diversity and in/out-of-network factors. See `home-mixer/scorers/ranking_scorer.rs` (`ScoringWeights`, `compute_weighted_score`, `apply_author_diversity`, `effective_oon_weight`).

### Positive signals (the algorithm wants these)

The weighted scorer adds each predicted probability × its weight (`home-mixer/scorers/weighted_scorer.rs:49-67`):

| Signal | Field | What to design for |
|---|---|---|
| **Follow author** | `follow_author_score` | Highest leverage. Posts that make viewers tap "Follow" boost everything else downstream. Lead with identity / authority / promise of more. |
| **Reply** | `reply_score` | Open loops, hot takes, fill-in-the-blanks, questions, civil-controversy. |
| **Repost** | `retweet_score` | Quotable one-liner, statement people want to be seen endorsing. |
| **Quote** | `quote_score` + `quoted_click_score` + `quoted_vqv_score` | Hooks that invite commentary, not just resharing. |
| **Share (DM)** | `share_via_dm_score` | "Send this to a friend" — niche/insider, funny, useful enough to DM. |
| **Share (copy link)** | `share_via_copy_link_score` | Off-platform shareable: screenshots, lists, mini-essays. |
| **Generic share** | `share_score` | Catch-all share. |
| **Dwell** | `dwell_score` + `dwell_time` | Length + density that holds attention. Long-form-on-X reads (1000-1500 chars) with a strong first line. |
| **Click** | `click_score` + `click_dwell_time` | Card / linked content that earns the click and the read. |
| **Profile click** | `profile_click_score` | Intriguing voice → "who is this?" |
| **Video Quality View** | `vqv_score` × VQV weight | Only counts when the video exceeds `MinVideoDurationMs` — see `home-mixer/scorers/ranking_scorer.rs:132-137` and `weighted_scorer.rs:72-81`. Sub-threshold videos get 0 video weight. |
| **Photo expand** | `photo_expand_score` | Images that reward tapping (detail, payoff in tap-to-zoom). |
| **Favorite (like)** | `favorite_score` | Real but secondary. Don't optimize purely for likes. |

### Negative signals (the algorithm suppresses these)

```
- not_interested_score × NotInterestedWeight
- block_author_score   × BlockAuthorWeight
- mute_author_score    × MuteAuthorWeight
- report_score         × ReportWeight
- not_dwelled_score    × NotDwelledWeight  (scrolled past with no dwell)
```

These weights are negative (`ranking_scorer.rs:83` — `negative_sum = -(not_interested + block + mute + report + not_dwelled)`). Posts that predictively trigger any of these get punished, even before a human actually reports.

### Structural modifiers (apply on top of the weighted score)

1. **Age filter** — `home-mixer/filters/age_filter.rs`. Posts older than `max_age` are dropped from the candidate set entirely. Old posts do not get re-served.
2. **Author diversity decay** — `home-mixer/scorers/author_diversity_scorer.rs`, `ranking_scorer.rs:186-217`. Within a single feed render, the Nth post from the same author is multiplied by `(1 - floor) × decay^N + floor`. Translation: do not flood. Same-author posts in rapid succession compete with each other and decay fast.
3. **OON penalty** — `home-mixer/scorers/oon_scorer.rs`, `ranking_scorer.rs:220-239`. Out-of-network candidates are multiplied by `OonWeightFactor < 1`. New users (`is_eligible_new_user`) get `NEW_USER_OON_WEIGHT_FACTOR` (looser). When the request is topic-filtered, `TopicOonWeightFactor` is used instead.
4. **In-network priority** — Thunder serves recent posts from followed accounts with sub-ms latency (`thunder/thunder_service.rs`, `home-mixer/sources/thunder_source.rs`). Followers are your floor; OON expansion is your ceiling.
5. **Mutual-follow Jaccard** — `home-mixer/candidate_hydrators/mutual_follow_jaccard_hydrator.rs`. Authors whose follower MinHash overlaps with the viewer's get a stronger feature signal. Build dense mutual graphs in your niche.
6. **Subscription post flag** — `home-mixer/candidate_hydrators/subscription_hydrator.rs`. X Premium subscription content is tracked separately and treated as a distinct tweet type (`tweet_type_metrics_hydrator.rs` → `SUBSCRIPTION_POST`).
7. **Author-followers bucketing** — `tweet_type_metrics_hydrator.rs:56-76`. The model conditions on follower buckets (0-100, 100-1K, 1K-10K, 10K-100K, 100K-1M, 1M+). Crossing a bucket changes how Phoenix scores you.
8. **Video duration bucketing** — `tweet_type_metrics_hydrator.rs:82-93`. ≤10s, 10-60s, >60s are separate features. Pick a bucket on purpose.
9. **Post age bucketing** — `tweet_type_metrics_hydrator.rs:95-112`. ≤30m, ≤1h, ≤6h, ≤12h, ≥24h. The first hour is its own feature — strong early engagement compounds.
10. **Served-size buckets** — same file, lines 116-129. Sessions with low served history (empty/near-empty feed) trigger different ranking. Posting during low-activity windows for your audience can land you in those buckets.

### Hard-limit filters (skip these or your reach is zero)

| Filter | File | What kills you |
|---|---|---|
| `VFFilter` | `home-mixer/filters/vf_filter.rs` + `scored_posts_server.rs:189-214` | Safety labels: NSFW_HIGH_PRECISION, NSFA, GORE_AND_VIOLENCE_HIGH_PRECISION, PDNA, EGREGIOUS_NSFW, DO_NOT_AMPLIFY, NSFW_TEXT, GROK_NSFA — drop or amplification-limit. |
| `MutedKeywordFilter` | `home-mixer/filters/muted_keyword_filter.rs` | If your post contains a viewer's muted keyword, instant exclusion from their feed. Common words = invisible to many. |
| `AuthorSocialgraphFilter` | `home-mixer/filters/author_socialgraph_filter.rs` | Blocked / muted authors are removed. Don't earn blocks. |
| `PreviouslySeenPostsFilter` | `home-mixer/filters/previously_seen_posts_filter.rs` | Impression bloom filter excludes already-seen posts. Reposting your own content fast = wasted impressions. |
| `RepostDeduplicationFilter` | `home-mixer/filters/retweet_deduplication_filter.rs` | Reposts of the same source dedup. Mass-RT chains collapse. |
| `SelfpostFilter` | `home-mixer/filters/self_tweet_filter.rs` | Viewers don't see their own posts in For You. Don't engagement-bait yourself. |
| `DedupConversationFilter` | `home-mixer/filters/dedup_conversation_filter.rs` | Multiple branches of one conversation get merged. Reply-spamming your own thread doesn't multiply slots. |

### Grox content understanding — the screen before scoring

`grox/` runs classifiers on every post before/around ranking. Signals visible from `grox/plans/`:

- `plan_initial_banger.py` + `grox/tasks/task_banger_screen.py` — a **"banger initial screen"** classifier flags candidates for wider distribution. Posts that pass the screen are flagged for additional inventory.
- `plan_safety_ptos.py` + `grox/tasks/task_safety_ptos_*.py` — PTOS policy categorization.
- `plan_spam_comment.py` + `grox/tasks/task_spam_detection.py` — spam classifier.
- `grox/embedder/multimodal_post_embedder_v5.py` — multimodal embedding (text + media) feeds Phoenix retrieval. Media-rich posts get richer representations.

**Implication:** Quality bar > volume. Posts that read as spam, low-effort, or off-policy get filtered before they reach ranking.

## Playbook: how to write toward the algorithm

When the user gives you a draft (or a topic), do this:

1. **Identify the engagement target.** Ask, or infer, which signal you're optimizing for. The weights are not equal — `follow_author` > `reply`/`share` > `dwell` > `favorite`. Pick one and design for it.
2. **Write a stop-scroll first line.** Dwell time and `not_dwelled_score` are decided in the first 1-2 seconds. Lead with concrete claim, surprising number, or named tension.
3. **Build the engagement hook on purpose:**
   - Reply-bait: open question, half-finished list, mild contrarian take. Avoid pure rage-bait (drives blocks/mutes/reports — negative weights).
   - Share-bait: insider knowledge, useful list, screenshot-able payoff. People DM/copy-link things that make them look smart or useful.
   - Follow-magnet: post #3 of a series, identity marker, "I do X, here's what I've learned" framing.
   - Dwell-bait: long-form (1000-1500 chars). Use line breaks. Earn each line.
4. **Add media on purpose, not by default.**
   - Image → only if photo_expand reward exists (zoom payoff).
   - Video → only if you can hold past `MinVideoDurationMs`. A 3-second loop gets the VQV weight zeroed out. Aim for the 10-60s bucket unless you have a real reason for >60s.
5. **Avoid hard-limit triggers.** No NSFW/gore-adjacent imagery without explicit context. No mass-link spam. No keyword-stuffed reply chains.
6. **Respect cadence.** Don't post 5 in a row — diversity decay punishes you in every viewer's feed. Space posts so each gets its own ranking slot.
7. **Earn the first hour.** Post age bucket ≤1h is a strong feature. Reply to early commenters fast — your replies trigger dwell + reply weights on the parent.
8. **Quote, don't bare-repost.** Quote posts get `quote_score` + `quoted_click_score` + `quoted_vqv_score` on top — a fresh weighted-score path that bare reposts don't have.
9. **Build mutuals in your niche.** MinHash Jaccard is computed per author (`mutual_follow_jaccard_hydrator.rs`). Following / being followed by a tight niche cluster boosts your scores inside that cluster.
10. **Don't reply-spam your own thread.** Conversation dedup will collapse it. One strong follow-up beats five.

## Output contract

When the user asks you to draft / rewrite for X virality, return:

1. **The post text** (or thread, with each tweet numbered, each ≤280 chars).
2. **Target signal** — which weighted scorer field you optimized for, with a one-line rationale.
3. **Risk flags** — anything that could trigger VF labels, muted keywords, spam classifier, or author-diversity decay.
4. **Post-publish action** — what to do in the first 60 minutes (reply to early commenters, pin if applicable, quote-amplify, etc.).

## Pre-publish checklist

Run through `checklist.md` (in this skill folder) before the user posts. If multiple items fail, rewrite before posting.

## References

- `references/algorithm-signals.md` — full signal catalog, every field mapped to a source file.
- `references/scoring-weights.md` — the weighted score formula, offset, and normalization.
- `references/filters-and-vf.md` — every filter, what it removes, how to avoid it.
- `references/recipes/` — copywriting recipe library by target signal (reply-bait shipped; dwell, share, follow-magnet, quote, threads in `ROADMAP.md`).
- `checklist.md` — pre-publish checklist.
- `tools/score_simulator.py` — heuristic weighted-score predictor (mirrors `home-mixer/scorers/ranking_scorer.rs` structure).
- `tools/verify_refs.py` — CI check that every source path cited in this skill still exists.
- `ROADMAP.md` — full sprint plan (Sprint 1 done; Sprint 2-6 mapped). Acts as the issue tracker until GitHub Issues is enabled on the repo.
