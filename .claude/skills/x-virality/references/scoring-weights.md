# Scoring Weights — The Formula

This file documents exactly how a post's final ranking score is computed, mapped to source.

## The weighted score formula

From `home-mixer/scorers/ranking_scorer.rs::compute_weighted_score` (and the simpler `home-mixer/scorers/weighted_scorer.rs`):

```
weighted_score =
    favorite_score        × FavoriteWeight
  + reply_score           × ReplyWeight
  + retweet_score         × RetweetWeight
  + photo_expand_score    × PhotoExpandWeight
  + click_score           × ClickWeight
  + profile_click_score   × ProfileClickWeight
  + vqv_score             × vqv_weight              # 0 if video < MinVideoDurationMs
  + share_score           × ShareWeight
  + share_via_dm_score    × ShareViaDmWeight
  + share_via_copy_link_score × ShareViaCopyLinkWeight
  + dwell_score           × DwellWeight
  + quote_score           × QuoteWeight
  + quoted_click_score    × QuotedClickWeight
  + quoted_vqv_score      × quoted_vqv_weight       # gated like vqv
  + dwell_time            × ContDwellTimeWeight
  + click_dwell_time      × ContClickDwellTimeWeight
  + follow_author_score   × FollowAuthorWeight
  + not_interested_score  × NotInterestedWeight     # negative weight
  + block_author_score    × BlockAuthorWeight       # negative weight
  + mute_author_score     × MuteAuthorWeight        # negative weight
  + report_score          × ReportWeight            # negative weight
  + not_dwelled_score     × NotDwelledWeight        # negative weight
```

Then `offset_score` normalizes the result so negative weighted-sums map to a [0, offset] range:

```
if total_sum == 0:
    final = max(combined, 0)
elif combined < 0:
    final = (combined + negative_sum) / total_sum × NEGATIVE_SCORES_OFFSET
else:
    final = combined + NEGATIVE_SCORES_OFFSET
```

After that, two more multipliers apply:

1. **Author diversity decay** (`ranking_scorer.rs:186-217`):
   ```
   multiplier(pos) = (1 - AuthorDiversityFloor) × AuthorDiversityDecay^pos + AuthorDiversityFloor
   ```
   `pos` is the rank-order position of this author within the candidate set, starting at 0. So the first post from author A is multiplied by `(1-floor) + floor = 1.0`. The second is `(1-floor)·decay + floor`. The third is `(1-floor)·decay² + floor`. Etc.

2. **OON factor** (`ranking_scorer.rs:220-239`, `oon_scorer.rs`):
   ```
   if not in_network:
       final *= effective_oon_weight(query)
   ```
   `effective_oon_weight` returns:
   - `TopicOonWeightFactor` if the request is topic-filtered
   - `NEW_USER_OON_WEIGHT_FACTOR` if the viewer is a new user with enough follows
   - `OonWeightFactor` otherwise

## Practical weight ordering

The actual numeric weights are runtime parameters (see `crate::params`), so the values can change. But the *structure* tells you the prioritization model the system was designed around:

1. **`follow_author_score`** — earning a follow is the single largest multiplier of future reach (every future post you make is rated against a new viewer who selected you).
2. **`reply_score`, `share_*`, `quote_score`** — multi-step engagements that signal real interest.
3. **`dwell_time` + `dwell_score`** — continuous reward for attention.
4. **`retweet_score`, `photo_expand_score`, `vqv_score`** — single-action confirmations.
5. **`favorite_score`, `click_score`, `profile_click_score`** — lightweight signals.
6. **Negative weights** — heavily penalize predicted dislike, block, mute, report, scroll-past.

This ordering is informed by the structure of the code and the offset logic (negative_sum is treated as a distinct term that fully normalizes the negative range), not by published numbers. Always look up runtime params before quoting numbers.

## Video weight gating

`home-mixer/scorers/weighted_scorer.rs:72-81` and `ranking_scorer.rs:132-137`:

```
vqv_weight = VqvWeight if video_duration_ms > MinVideoDurationMs else 0
```

Quote VQV has an additional `EnableQuotedVqvDurationCheck` flag. **Sub-threshold videos get zero video credit.**

## Implications for writing posts

1. **Optimize for the biggest weight you can credibly hit.** A post that drives a follow is worth more than one that drives 10 likes.
2. **Compound positive signals.** A reply + dwell + share on the same post stacks linearly — the weighted score adds them.
3. **Predicted negatives kill you, not just actual ones.** The model predicts `not_interested_score` etc. for *every* viewer before serving. If your post pattern-matches to historical not-interested posts, you get suppressed before anyone sees it.
4. **Diversity decay caps cadence.** Posting 5 times in 10 minutes means each post fights the previous one — post 5 gets multiplied by `(1-floor)·decay^4 + floor`, which can be small.
5. **OON factor < 1 always (in normal mode).** You will always be down-weighted to OON viewers vs in-network ones. Earning follows raises every future post out of the OON penalty for those viewers.
6. **Video < MinDuration is wasted.** If you're going to put a video on a post, make it long enough to count. Otherwise drop it and use an image.
