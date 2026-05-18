# Pre-Publish Checklist

Run this before posting. If two or more items fail, rewrite.

## Hook (first 1-2 lines)

- [ ] First line stops the scroll. Specific number, named tension, claim, or question — not "I think" / "guys" / "so..."
- [ ] First line works without seeing the rest. No dependence on the thread or media.
- [ ] No common muted keyword in the first line (airdrop, sex, etc. block reach for muters).

## Engagement target

Choose **one** and write to it:

- [ ] **Follow** — identity post. Reader thinks "I want more of this voice."
- [ ] **Reply** — open question / mild contrarian take / fill-in-the-blank.
- [ ] **Share (DM)** — insider, useful, or funny enough that someone wants a friend to see it.
- [ ] **Share (copy link)** — screenshot-able payoff. Lists, mini-essays, charts.
- [ ] **Dwell** — long-form (1000-1500 chars), earned line by line.
- [ ] **Quote** — invites commentary, not just reshare.

## Format

- [ ] Length matches the target. Reply-bait < 280; dwell post 800-1500; thread only if each tweet stands alone.
- [ ] Line breaks where they earn attention. No wall of text.
- [ ] If thread: each tweet is itself shareable.

## Media

- [ ] If image: tap-to-zoom payoff exists (detail, punchline, data).
- [ ] If video: duration ≥ `MinVideoDurationMs` threshold. Sub-threshold videos get 0 video weight — drop or extend.
- [ ] Video duration is in a bucket on purpose: ≤10s (loop/hook), 10-60s (clip), >60s (segment).
- [ ] If quote post: the quoted post itself rewards engagement (you inherit its quoted-click/VQV signals).

## Risk audit

- [ ] No NSFW / gore / violence content without explicit, contextual reason (VF labels drop reach).
- [ ] No spam patterns: no excessive repetition, no link-stuffing, no mass-reply chains.
- [ ] No mass-mute / mass-block triggers: no rage-bait at identity groups, no harassment language.
- [ ] Not a near-duplicate of a recent post of yours (previously-seen filter + diversity decay).
- [ ] Brand-safety friendly text (avoid slur-adjacency, gore-adjacent vocabulary unless the topic requires it).

## Cadence

- [ ] Your last post was at least 30-60 minutes ago. Same author within a single feed render decays — `(1 - floor) × decay^N + floor`.
- [ ] No more than ~5 posts in 24h unless threaded.
- [ ] If threading, post the whole thread together — don't drip-feed.

## Timing

- [ ] Posting now puts you in the `TWEET_AGE_LTE_30_MINUTES` and `LTE_1_HOUR` buckets for your audience's active hours.
- [ ] You're free in the next 60 minutes to reply to early commenters (each reply drives dwell + reply weight on the parent).

## Distribution boost

- [ ] You can quote-amplify with at least one mutual when posted.
- [ ] If niche post: at least 2-3 mutuals in your MinHash cluster will likely engage in the first hour.
- [ ] (Optional) Subscription / Premium content tag is set if applicable.

## Post-publish (first 60 minutes)

- [ ] Reply to early commenters within 5-10 minutes of their reply (boosts dwell + reply weight on your post, your reply gets ranked too).
- [ ] Do NOT mass-reply to your own thread — `DedupConversationFilter` collapses it.
- [ ] If a reply has unusual traction, consider quote-amplifying with extra context.
- [ ] Do NOT delete and repost a similar tweet — previously-seen bloom filter blocks it for the same viewers.
