# Filters & Visibility Filtering — What Kills Reach

The candidate pipeline runs filters at two stages (see `home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs`). If any filter drops your post, your weighted score is irrelevant — you simply don't appear.

## Pre-scoring filters

Located in `home-mixer/filters/`. These run *before* Phoenix is invoked.

| Filter | What it drops | How to avoid |
|---|---|---|
| `DropDuplicatesFilter` (`drop_duplicates_filter.rs` via `candidate-pipeline/filter.rs`) | Duplicate post IDs in the candidate set. | N/A (internal). |
| `CoreDataHydrationFilter` (`core_data_hydration_filter.rs`) | Posts whose core metadata failed to hydrate. | Don't delete the post mid-pipeline. |
| `AgeFilter` (`age_filter.rs`) | Posts older than `max_age`. | Old posts won't be resurfaced. Don't expect re-discovery of last month's tweet. |
| `SelfpostFilter` (`self_tweet_filter.rs`) | The viewer's own posts. | Don't engagement-bait by viewing your own feed. |
| `RepostDeduplicationFilter` (`retweet_deduplication_filter.rs`) | Reposts of the same source post. | Mass-retweet chains collapse to one slot. |
| `IneligibleSubscriptionFilter` (`ineligible_subscription_filter.rs`) | Paywalled content the viewer can't access. | If you post Premium-only, expect smaller reach. |
| `PreviouslySeenPostsFilter` (`previously_seen_posts_filter.rs`) + `previously_seen_posts_backup_filter.rs` | Posts the impression bloom filter says were already seen. | Don't recycle the same exact tweet — it's invisible to past viewers. |
| `PreviouslyServedPostsFilter` (`previously_served_posts_filter.rs`) | Posts already served in the session. | N/A (internal). |
| `MutedKeywordFilter` (`muted_keyword_filter.rs`) | Posts whose tokenized text matches a viewer's muted keywords. | **Stop using globally muted words** ("airdrop", "crypto", common spam terms). They make you invisible to anyone who muted them. |
| `AuthorSocialgraphFilter` (`author_socialgraph_filter.rs`) | Authors blocked or muted by the viewer. | Don't earn blocks/mutes — they compound (every block = permanent exclusion from that viewer). |
| `TopicIdsFilter` (`topic_ids_filter.rs`) + `new_user_topic_ids_filter.rs` | Posts off-topic for a topic-filtered feed. | If posting for a specific topic feed, tag/classify clearly. |
| `VideoFilter` (`video_filter.rs`) | Video posts when the request set `exclude_videos`. | N/A (user setting). |
| `AncillaryVFFilter` (`ancillary_vf_filter.rs`) | Ancillary visibility filtering checks. | See VF labels below. |

## Post-selection filters

| Filter | What it drops |
|---|---|
| `VFFilter` (`vf_filter.rs`) | Posts whose `visibility_reason` says drop, based on safety labels. |
| `DedupConversationFilter` (`dedup_conversation_filter.rs`) | Multiple branches of the same conversation thread — only one survives. |

## Visibility Filtering (VF) labels

From `home-mixer/scored_posts_server.rs::safety_label_to_proto` and `home-mixer/filters/vf_filter.rs`:

| Safety label | Effect |
|---|---|
| `NSFW_HIGH_PRECISION` | High-confidence NSFW → drop / restrict. |
| `NSFW_HIGH_RECALL` | Broader NSFW → restrict. |
| `NSFA_HIGH_PRECISION`, `NSFA_HIGH_RECALL` | Not-Safe-For-Ads / sensitive. |
| `NSFA_KEYWORDS_HIGH_PRECISION` | NSFA based on keyword detection. |
| `GORE_AND_VIOLENCE_HIGH_PRECISION`, `GORE_AND_VIOLENCE_REPORTED_HEURISTICS` | Gore/violence → drop. |
| `NSFW_REPORTED_HEURISTICS` | Reported NSFW. |
| `NSFW_CARD_IMAGE` | NSFW card preview. |
| `NSFW_TEXT` | NSFW text content. |
| `DO_NOT_AMPLIFY` | Hard limit — explicitly do not amplify. |
| `NSFA_COMMUNITY_NOTE` | Community Note marked NSFA. |
| `PDNA` | Photo DNA match (CSAM hash). |
| `EGREGIOUS_NSFW` | Highest-severity NSFW. |
| `GROK_NSFA`, `GROK_NSFA_LIMITED`, `GROK_SFA` | Grok classifier verdicts. |
| `NSFA_LIMITED_INVENTORY` | Limited inventory NSFA. |

**Practical implication:** Any of these on your post drops you out of For You or hard-limits amplification. They are applied by Grok safety classifiers (`grox/plans/plan_safety_ptos.py`, `plan_post_safety.py`).

## Brand safety verdict

From `home-mixer/models/brand_safety.rs` and `home-mixer/scored_posts_server.rs`:

```
BrandSafetyVerdict: LowRisk | MediumRisk | (others)
```

`MediumRisk` is the "avoid" verdict — affects ad adjacency (`home-mixer/ads/util.rs::has_avoid`). Posts marked MediumRisk lose monetization adjacency and signal lower-quality to the ads blender.

## Grox screens (the pre-filters before filters)

Even before the candidate pipeline filters, `grox/` content understanding decides if your post is eligible for the candidate corpus at all.

| Plan | What it screens |
|---|---|
| `grox/plans/plan_spam_comment.py` (`task_spam_detection.py`) | Spam → blocked from amplification. Repetitive content, mass-reply patterns, link-spam triggers this. |
| `grox/plans/plan_safety_ptos.py` (`task_safety_ptos_category.py`, `task_safety_ptos_policy.py`) | PTOS policy categorization. Posts categorized into policy violations are restricted. |
| `grox/plans/plan_post_safety.py` | Post safety classification. |
| `grox/plans/plan_initial_banger.py` (`task_banger_screen.py`) | "Banger" screen — passes promising posts for amplification. **Failing this is not a penalty, but passing it is a boost.** |

## Cheatsheet: post-killers in order of severity

1. **PDNA / EGREGIOUS_NSFW / GORE labels** — drop, no recovery.
2. **DO_NOT_AMPLIFY label** — explicit hard limit.
3. **PTOS policy violation** — restricted.
4. **Spam classifier hit** — restricted.
5. **NSFW / NSFA labels** (without context) — heavily limited.
6. **Earning blocks / mutes** — permanent for those viewers + negative weight (`block_author_score`, `mute_author_score`).
7. **Common muted keywords in post body** — invisible to muters.
8. **`not_interested` clicks** — negative weight, training signal.
9. **MediumRisk brand-safety verdict** — limits ad adjacency.
10. **Author-diversity decay from rapid posting** — soft, fixable by spacing.
