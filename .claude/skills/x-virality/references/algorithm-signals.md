# Algorithm Signals — Source-Mapped Catalog

Every signal the X For You algorithm reads, mapped to the file in this repo. Use this when explaining *why* a copywriting choice helps or hurts.

## Phoenix prediction outputs

The Phoenix transformer outputs probabilities for these actions (`phoenix/recsys_model.py`, surfaced as `PhoenixScores` in `home-mixer/models/candidate.rs`):

```
favorite_score, reply_score, retweet_score, photo_expand_score,
click_score, profile_click_score, vqv_score, share_score,
share_via_dm_score, share_via_copy_link_score, dwell_score,
quote_score, quoted_click_score, quoted_vqv_score,
dwell_time, click_dwell_time,
follow_author_score,
not_interested_score, block_author_score, mute_author_score,
report_score, not_dwelled_score
```

Each is combined with its weight in `home-mixer/scorers/ranking_scorer.rs::compute_weighted_score` and `home-mixer/scorers/weighted_scorer.rs::compute_weighted_score`.

## Query hydrators — what the algorithm knows about the viewer

Every field below is fetched per request before ranking. Knowing the field exists tells you what behavior gets tracked.

| File (in `home-mixer/query_hydrators/`) | Signal |
|---|---|
| `user_action_seq_query_hydrator.rs` | Engagement history (the user's recent likes/replies/reposts/quotes/dwells). This is the Phoenix model's most important input. |
| `user_features_query_hydrator.rs` | Static user features (preferences, settings). |
| `followed_user_ids_query_hydrator.rs` | Following list (used for in-network sourcing). |
| `mutual_follow_query_hydrator.rs` | MinHash of follower graph (Jaccard similarity with candidate authors). |
| `subscribed_user_ids_query_hydrator.rs` | X Premium subscriptions. |
| `blocked_user_ids_query_hydrator.rs`, `muted_user_ids_query_hydrator.rs` | Authors to exclude. |
| `followed_grok_topics_query_hydrator.rs`, `inferred_grok_topics_query_hydrator.rs` | Topics the user follows or is inferred to be interested in. |
| `followed_starter_packs_query_hydrator.rs` | Starter-pack subscriptions. |
| `impression_bloom_filter_query_hydrator.rs`, `impressed_posts_query_hydrator.rs` | Already-seen post IDs — your post will not be re-served to the same viewer. |
| `served_history_query_hydrator.rs` | Recently served candidates. |
| `past_request_timestamps_query_hydrator.rs` | Session timing — informs freshness logic. |
| `ip_query_hydrator.rs` | IP / geo signal. |
| `user_demographics_query_hydrator.rs`, `user_inferred_gender_query_hydrator.rs` | Demographic features. |
| `retrieval_sequence_query_hydrator.rs`, `scoring_sequence_query_hydrator.rs` | Sequence representations used as model input. |
| `cached_posts_query_hydrator.rs` | Recent cache — affects freshness vs reuse. |

## Candidate hydrators — what the algorithm knows about your post

| File (in `home-mixer/candidate_hydrators/`) | Signal |
|---|---|
| `core_data_candidate_hydrator.rs` | Tweet text, author, basic metadata. |
| `engagement_counts_hydrator.rs` | `fav_count`, `reply_count`, `repost_count`, `quote_count`. Early absolute counts feed downstream models. |
| `gizmoduck_hydrator.rs` | Author info: screen name, follower count, verification status. |
| `has_media_hydrator.rs` | Whether the post has media. |
| `video_duration_candidate_hydrator.rs` | Video duration — gates VQV weight. |
| `subscription_hydrator.rs` | X Premium subscription author flag. |
| `language_code_hydrator.rs` | Language code. |
| `mutual_follow_jaccard_hydrator.rs` | MinHash Jaccard between viewer and candidate author. |
| `following_replied_users_hydrator.rs` | Whether the author has replied to people the viewer follows. |
| `quote_hydrator.rs` | Quote post expansion + quoted-post features. |
| `blocked_by_hydrator.rs` | Whether the viewer is blocked by the author. |
| `filtered_topics_hydrator.rs` | Topic classification of the post. |
| `ads_brand_safety_hydrator.rs`, `ads_brand_safety_vf_hydrator.rs` | Brand safety verdict — affects ad adjacency + signal. |
| `vf_candidate_hydrator.rs` | Visibility filtering labels (NSFW / gore / DNA / NSFA / etc.). |
| `tweet_type_metrics_hydrator.rs` | Bitset of tweet-type buckets (see below). |
| `in_network_candidate_hydrator.rs` | In-network flag. |

## Tweet-type bitset (`tweet_type_metrics_hydrator.rs`)

The model conditions on these explicit buckets. Each is a feature your post is or isn't in:

- `RETWEET`, `REPLY`, `SUBSCRIPTION_POST`, `HAS_ANCESTORS`, `IN_NETWORK`, `FULL_SCORING_SUCCEEDED`, `ANY_CANDIDATE`
- Author followers: `0_100`, `100_1K`, `1K_10K`, `10K_100K`, `100K_1M`, `1M_PLUS`
- Video: `VIDEO`, `VIDEO_LTE_10_SEC`, `VIDEO_BT_10_60_SEC`, `VIDEO_GT_60_SEC`
- Age: `TWEET_AGE_LTE_30_MINUTES`, `LTE_1_HOUR`, `LTE_6_HOURS`, `LTE_12_HOURS`, `GTE_24_HOURS`
- Session: `EMPTY_REQUEST`, `NEAR_EMPTY`, `SERVED_SIZE_LESS_THAN_5/10/20`

Crossing a bucket changes how the model scores you. Three implications:

1. **First hour matters** — separate feature space.
2. **Follower-bucket jumps unlock new ranking territory** — passing 100, 1K, 10K, 100K each open new neighborhoods.
3. **Video duration choice is a feature**, not a free variable.

## Sources — where candidates come from

`home-mixer/sources/`:

- `thunder_source.rs` — in-network posts (Thunder = realtime in-memory store of recent posts).
- `phoenix_source.rs` — out-of-network retrieval via Phoenix two-tower.
- `phoenix_moe_source.rs` — Phoenix MoE candidates.
- `phoenix_topics_source.rs` — topic-filtered Phoenix candidates.
- `tweet_mixer_source.rs` — legacy tweet mixer.
- `who_to_follow_source.rs` — WTF entries.
- `ads_source.rs` — ad candidates.
- `prompts_source.rs` — prompt cards.
- `push_to_home_source.rs` — push-to-home injections.
- `cached_posts_source.rs` — cache reuse.

## Grox content understanding

`grox/plans/` shows the plans that run over content before ranking:

- `plan_initial_banger.py` (`task_banger_screen.py`) — banger-initial-screen classifier. Posts that pass get flagged for amplification.
- `plan_post_safety.py`, `plan_safety_ptos.py` — safety + policy classification.
- `plan_spam_comment.py` (`task_spam_detection.py`) — spam classifier.
- `plan_post_embedding_v5*.py` — multimodal embedding (`grox/embedder/multimodal_post_embedder_v5.py`). Media + text embed jointly.
- `plan_reply_ranking.py` — reply ranking. Quality of your *replies* on others' posts is its own ranking pipeline.
- `plan_master.py` — orchestrates the others.

## Sequence: how a post becomes a recommendation

1. **Thunder ingests** your post via Kafka in realtime (`thunder/kafka/`, `thunder/posts/`, `thunder/thunder_service.rs`).
2. **Grox classifies** it: spam screen, safety screen, banger screen, multimodal embedding (`grox/dispatcher.py`, `grox/engine.py`).
3. **Phoenix indexes** the embedding for retrieval.
4. On every For You request:
   - Query hydrators load the viewer's state.
   - Sources retrieve candidates (Thunder for in-network, Phoenix for OON).
   - Candidate hydrators load your post's metadata + features.
   - Pre-scoring filters drop ineligibles (age, muted-keyword, blocked, dup, etc.).
   - **Phoenix scorer** predicts each action probability.
   - **Weighted scorer** combines into one score.
   - **Author diversity scorer** decays repeated authors.
   - **OON scorer** down-weights out-of-network.
   - Selector takes top-K.
   - Post-selection filters apply VF + conversation dedup.
5. Side effects log impression, update served history, publish to Kafka for the feedback loop (`home-mixer/side_effects/`).

This loop is closed: your post's served impressions feed back into Phoenix training data, so early engagement disproportionately shapes long-tail reach.
