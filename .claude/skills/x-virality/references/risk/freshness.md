# Freshness & First-Hour Playbook

Source: `home-mixer/filters/age_filter.rs`, `home-mixer/candidate_hydrators/tweet_type_metrics_hydrator.rs:95-112` (age buckets), `home-mixer/sources/thunder_source.rs`, `thunder/thunder_service.rs`.

X's For You has two freshness mechanics:

1. **Age filter** — posts older than `max_age` are dropped from the candidate set entirely.
2. **Age buckets** — `TWEET_AGE_LTE_30_MINUTES`, `LTE_1_HOUR`, `LTE_6_HOURS`, `LTE_12_HOURS`, `GTE_24_HOURS`. The Phoenix model conditions on these.

Old posts don't get rediscovered. The window in which you can earn engagement is bounded. The first hour is its own feature space.

---

## The age filter

`home-mixer/filters/age_filter.rs`:

```rust
fn is_within_age(&self, tweet_id: u64) -> bool {
    duration_since_creation_opt(tweet_id)
        .map(|age| age <= self.max_age)
        .unwrap_or(false)
}
```

Posts older than `max_age` are filtered out. The actual `max_age` is a runtime parameter, but the floor is clear: old posts are not candidates. Don't expect a brilliant post from last month to suddenly take off.

---

## The age buckets

`home-mixer/candidate_hydrators/tweet_type_metrics_hydrator.rs:95-112`:

```rust
if age_ms <= THIRTY_MINUTES_MS {
    true_tweet_types.insert(TWEET_AGE_LTE_30_MINUTES);
}
if age_ms <= ONE_HOUR_MS {
    true_tweet_types.insert(TWEET_AGE_LTE_1_HOUR);
}
if age_ms <= SIX_HOURS_MS {
    true_tweet_types.insert(TWEET_AGE_LTE_6_HOURS);
}
if age_ms <= TWELVE_HOURS_MS {
    true_tweet_types.insert(TWEET_AGE_LTE_12_HOURS);
}
if age_ms >= TWENTY_FOUR_HOURS_MS {
    true_tweet_types.insert(TWEET_AGE_GTE_24_HOURS);
}
```

These bits are part of the candidate's tweet-type bitset, used as features in Phoenix. The model has learned different patterns per bucket. The 30-minute bucket is the strongest "fresh" signal.

**Note:** buckets are nested. A 20-minute-old post is in `LTE_30_MINUTES`, `LTE_1_HOUR`, `LTE_6_HOURS`, AND `LTE_12_HOURS` simultaneously. The freshest bucket bit is the most informative signal.

---

## Thunder — the realtime in-network path

`home-mixer/sources/thunder_source.rs` calls Thunder for in-network candidates. Thunder is an in-memory store of recent posts (`thunder/thunder_service.rs`, `thunder/posts/`). It's optimized for sub-millisecond lookups of "recent posts from accounts the viewer follows."

The retention window in Thunder is bounded (`thunder/posts/` trims old posts). A post that ages out of Thunder is no longer served via the in-network path — it has to be retrieved via Phoenix OON (where the OON penalty applies).

**Implication:** the freshest content path to your followers is via Thunder. Once your post ages out, even followers see it via OON. Earn the in-network slot in the first hours.

---

## Strategy 1 — Front-load engagement in the first hour

The first hour is its own feature space (`TWEET_AGE_LTE_30_MINUTES`, `LTE_1_HOUR`). Engagement here gets the algorithm's freshest signal value.

**Concrete:**
- Post when at least some of your audience is online (avoid 3am unless your audience is global).
- Be available to reply to early commenters in the first 60 minutes.
- Each reply you make on your own post drives `dwell_score`, `reply_score`, and triggers `following_replied_users_hydrator.rs` for downstream distribution.

Empty first hours mean Phoenix sees the post hasn't earned engagement. The early-engagement signal compounds: a post with strong first-hour signal gets retrieved more often, accumulating more signal, etc. The opposite is also true.

---

## Strategy 2 — Don't expect long-tail amplification

If a post doesn't take off in the first 6-12 hours, it probably won't. The age filter eventually drops it; the age buckets shift toward `LTE_6_HOURS` → `LTE_12_HOURS` → `GTE_24_HOURS`. After 24 hours, the post sits in the long-tail bucket where ranking is much rarer.

**Implication:** don't delete a "slow start" post immediately, but also don't expect it to be a sleeper hit. Plan the next post.

---

## Strategy 3 — Quote-amplify when timely

If your post gets a quote-worthy response or a news event makes it relevant again, quote it with the new context. The quote is a NEW post — fresh age. The original is embedded.

This is the only legitimate way to "re-surface" a post that's aged out.

---

## Strategy 4 — Time your posts to your audience's first hour

Different audiences are online at different times. If your audience is US-East tech professionals, posting at 8am ET (just before-work scrolling) and 6pm ET (post-work scrolling) hits two peak windows. Posting at noon Pacific (when half your audience is in meetings) hits weaker engagement, which depresses first-hour signal.

**Concrete:**
- Identify two peak windows per day from your existing engagement data.
- Post at the start of one peak window — gives the post 60-90 minutes of active audience.
- Avoid posting in the dead zones (typically late-night for your audience).

---

## Strategy 5 — Don't post during news black holes

When major news events dominate, your generic post drowns. Even if it's good, the first-hour engagement is depressed because attention is elsewhere. Either:
- Time your post to peak windows that DON'T overlap with news cycles.
- Make your post about the news (with care for VF / brand-safety risk).
- Skip that day.

---

## Strategy 6 — Reply to early signal

If a post starts taking off in the first 15-30 minutes, double down:
- Reply to top early commenters with substance (their reply is now your reply to a follower of theirs → in-network distribution boost via `following_replied_users_hydrator.rs`).
- Quote-amplify the post with extra context if a new angle emerged.
- Pin it if you're going to be talking about it.

If a post is dead in the first 30-60 minutes, don't try to revive it. Move on.

---

## What we don't recommend

- **Posting and disappearing.** First hour is when your engagement work has the most multiplier.
- **Bumping your own post.** Replying to your own post mostly hits `DedupConversationFilter` (`home-mixer/filters/dedup_conversation_filter.rs`) — you don't get the boost.
- **Re-posting the same content fresh.** `PreviouslySeenPostsFilter` blocks it for anyone who saw the first, and the spam classifier catches the pattern.

## Output contract (when invoked)

When the user asks about timing / freshness, return:

1. Their audience's two peak windows based on what you can infer.
2. The optimal posting time today.
3. A 60-minute post-publish action plan.
4. A "kill it after 6 hours" check: are they over-investing in a post that didn't catch?
