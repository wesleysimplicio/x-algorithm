# Visibility Filter (VF) Labels — Avoidance Guide

Source: `home-mixer/scored_posts_server.rs::safety_label_to_proto`, `home-mixer/filters/vf_filter.rs`, `home-mixer/candidate_hydrators/vf_candidate_hydrator.rs`.

VF labels are the algorithm's hardest limit. Posts with a Drop verdict are removed from the candidate set entirely (`vf_filter.rs`). Posts with non-Drop reasons (limited amplification, sensitive media) are still constrained.

You cannot out-weight a Drop verdict. The only winning move is not to trigger one.

---

## The labels, from `scored_posts_server.rs::safety_label_to_proto`

```rust
SafetyLabelType::NSFW_HIGH_PRECISION => HM::NsfwHighPrecision,
SafetyLabelType::NSFW_HIGH_RECALL => HM::NsfwHighRecall,
SafetyLabelType::NSFA_HIGH_PRECISION => HM::NsfaHighPrecision,
SafetyLabelType::NSFA_KEYWORDS_HIGH_PRECISION => HM::NsfaKeywordsHighPrecision,
SafetyLabelType::GORE_AND_VIOLENCE_HIGH_PRECISION => HM::GoreAndViolenceHighPrecision,
SafetyLabelType::NSFW_REPORTED_HEURISTICS => HM::NsfwReportedHeuristics,
SafetyLabelType::GORE_AND_VIOLENCE_REPORTED_HEURISTICS => HM::GoreAndViolenceReportedHeuristics,
SafetyLabelType::NSFW_CARD_IMAGE => HM::NsfwCardImage,
SafetyLabelType::DO_NOT_AMPLIFY => HM::DoNotAmplify,
SafetyLabelType::NSFA_COMMUNITY_NOTE => HM::NsfaCommunityNote,
SafetyLabelType::PDNA => HM::Pdna,
SafetyLabelType::EGREGIOUS_NSFW => HM::EgregiousNsfw,
SafetyLabelType::GROK_NSFA => HM::GrokNsfa,
SafetyLabelType::NSFW_TEXT => HM::NsfwText,
SafetyLabelType::NSFA_LIMITED_INVENTORY => HM::NsfaLimitedInventory,
SafetyLabelType::GROK_NSFA_LIMITED => HM::GrokNsfaLimited,
SafetyLabelType::NSFA_HIGH_RECALL => HM::NsfaHighRecall,
SafetyLabelType::GROK_SFA => HM::GrokSfa,
```

---

## Severity tiers (hard-drop → limited)

### Tier 1 — Hard drop

These get filtered out completely via `vf_filter.rs::should_drop`. Your post is invisible to anyone in For You / topics / following surfaces.

- **`PDNA`** — Photo DNA match (CSAM). Absolute hard limit. If you trigger this by accident, the account is at risk, not just the post.
- **`EGREGIOUS_NSFW`** — highest-severity NSFW. Drop.
- **`DO_NOT_AMPLIFY`** — explicit "do not amplify" classifier verdict. Drop.
- **`GORE_AND_VIOLENCE_HIGH_PRECISION`** — high-confidence gore/violence imagery. Drop.

### Tier 2 — Amplification-limited

These don't drop but heavily restrict reach. Often visible only to followers or via direct link.

- **`NSFW_HIGH_PRECISION`** — high-confidence NSFW imagery.
- **`NSFW_REPORTED_HEURISTICS`** — flagged by reports.
- **`NSFW_CARD_IMAGE`** — NSFW image in a card preview (your linked content).
- **`NSFW_TEXT`** — NSFW text content.
- **`GORE_AND_VIOLENCE_REPORTED_HEURISTICS`** — flagged by reports for gore/violence.

### Tier 3 — NSFA (Not Safe For Ads) restrictions

These don't drop from For You but limit monetization and possibly amplification.

- **`NSFA_HIGH_PRECISION`** / **`NSFA_HIGH_RECALL`** — classifier verdicts.
- **`NSFA_KEYWORDS_HIGH_PRECISION`** — triggered by keyword detection.
- **`NSFA_LIMITED_INVENTORY`** — limited ad inventory available adjacent.
- **`NSFA_COMMUNITY_NOTE`** — Community Note marked the post NSFA.

### Tier 4 — Grok verdicts

These are produced by Grok content classifiers (`grox/plans/plan_safety_ptos.py`).

- **`GROK_NSFA`** / **`GROK_NSFA_LIMITED`** — Grok's NSFA verdict.
- **`GROK_SFA`** — Grok's Safe-For-Ads verdict (a positive label).

### Tier 5 — Broader-recall NSFW (still limits, lower confidence)

- **`NSFW_HIGH_RECALL`** — broader detection, lower confidence.

---

## What triggers each label

These are heuristics, not exhaustive — the classifiers learn from data:

### NSFW (imagery)
- Nudity, partial nudity, suggestive imagery.
- Adult content, even if cropped.
- Lingerie / underwear shots that aren't editorial / news context.

### NSFW_TEXT
- Sexually explicit text.
- Suggestive content even without imagery.

### Gore / violence
- Blood, wounds, injury imagery.
- Footage of real violence (war, attacks, accidents) without contextual framing.
- Animal cruelty imagery.

### NSFA (broader — limits ads / amplification)
- Strong profanity in primary text.
- Politically inflammatory content (depending on context).
- Drug references, even casual.
- Content adjacent to but not crossing NSFW (e.g., explicit discussion of sexual topics).

### DO_NOT_AMPLIFY
- Triggered by Grok policy classifier (`grox/plans/plan_safety_ptos.py`, `grox/tasks/task_safety_ptos_policy.py`).
- Specific PTOS policy violations.
- Content X has explicitly classified as not-for-amplification.

### Community Note (`NSFA_COMMUNITY_NOTE`)
- Posts with a community-added context note marking it as misleading or NSFA.
- This is human-driven, not classifier-driven.

---

## Avoidance strategy

### Image and video

1. **Audit imagery before posting.** Anything suggestive, bloody, or shock-value → high VF risk.
2. **Card previews matter.** If you link to a page with NSFW imagery in its preview card, `NSFW_CARD_IMAGE` can fire on your post even if your text is clean.
3. **Crops don't help.** Classifiers see the whole image as posted; cropping doesn't fool them.

### Text

1. **Strong profanity in text** → NSFW_TEXT or NSFA triggers.
2. **NSFA keywords** → `NSFA_KEYWORDS_HIGH_PRECISION`. Avoid clusters of common adult-content keywords even in clean context.
3. **Mockery of identity groups** → drives reports, which feed `NSFW_REPORTED_HEURISTICS` / `GORE_AND_VIOLENCE_REPORTED_HEURISTICS` over time. The reported-heuristics signal compounds; a history of reports lowers your default scoring.

### Community Note prevention

1. **Cite sources** — if your post makes a factual claim, link or attribute. Community Notes flag unsourced surprising claims.
2. **Don't recycle screenshots without attribution.**
3. **Numerical claims need a source.** Made-up numbers attract Notes.

### Topical hazards

Some topics inherently risk VF labels even when discussed thoughtfully:
- Discussions of real-world violence — risk gore/violence labels.
- Discussions of adult topics for educational purposes — risk NSFW labels.
- Mental health / self-harm content — risks PTOS policy via Grok.

These can be posted safely with careful framing, but they need explicit contextual framing in the first lines, not at the end.

---

## What to do if you suspect a label is applied

You can't see the labels directly (they're internal). Indirect signals:
- A post that's getting "weird" engagement (likes from followers but no OON impressions) — possible amplification-limited label.
- A post that doesn't appear in your own For You feed when logged out — possible drop verdict.
- A sudden drop-off in OON reach — possible classifier hit, or community note.

**Response:** delete the post, learn from it, don't reproduce the trigger pattern.

---

## Brand safety as a softer cousin

`home-mixer/models/brand_safety.rs` defines `BrandSafetyVerdict` (`LowRisk` / `MediumRisk`). `MediumRisk` triggers `has_avoid` in `home-mixer/ads/util.rs` — your post becomes "avoid for ads" but isn't VF-labeled. This affects monetization more than reach, but the verdict is in the same family of classifiers — content that earns MediumRisk repeatedly is at higher risk of crossing into VF territory.

## Output contract (when invoked)

When the user shows you a draft that might risk VF labels, return:

1. Per-label risk audit: which label(s) the draft might trigger.
2. The trigger element (specific phrasing, image content, link).
3. Reframe or remove recommendation.
4. If unsalvageable: how to address the topic without crossing the label boundary.
