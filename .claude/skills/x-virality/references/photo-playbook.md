# Photo Playbook

Target signal: `photo_expand_score`.
See `home-mixer/scorers/ranking_scorer.rs` (`PhotoExpandWeight`), `home-mixer/candidate_hydrators/has_media_hydrator.rs`.

Photo expand is the "did the reader tap to enlarge" signal. It's a positive weight in the formula. Images are the safer media choice when video gating is unsuitable — no duration threshold, no completion risk.

The Grox multimodal embedder (`grox/embedder/multimodal_post_embedder_v5.py`) generates a joint text+image embedding. A well-composed image isn't just a photo_expand candidate — it shifts your post's representation in Phoenix's retrieval index, helping it find viewers who engage with similar media.

---

## What earns a tap-to-expand

`photo_expand_score` fires when the reader taps the image to see it at full size. So the image has to be worth enlarging. The thumbnail in feed already shows enough that they could scroll past — your job is to make them want more detail.

### Good reasons to expand

1. **Detail payoff** — the image has text/data/visual elements that don't read at thumbnail size.
2. **Surprising composition** — something in the frame that the reader registers but can't quite parse without enlarging.
3. **Annotated screenshot** — arrows, highlights, callouts that need the larger frame.
4. **Chart / data viz** — axes, labels, multiple data points.
5. **Faces / expressions** — humans intuitively expand to read expressions.

### Bad reasons to post an image at all

- Decorative stock photo — adds no signal, dilutes the post's representation in the multimodal embedding.
- AI-generated filler — risks looking like spam, and Grok content classifiers (`grox/classifiers/content/`) may catch the pattern.
- Reused screenshots from someone else without attribution — Community Note risk (`NSFA_COMMUNITY_NOTE` in `home-mixer/scored_posts_server.rs::safety_label_to_proto`).

---

## Composition patterns

### Pattern 1 — Text-in-image (mini-essay screenshot)

Post a screenshot of formatted text — a quote, a paragraph, a definition. The thumbnail shows enough to draw the eye; the expand reveals the full readable text.

**Why this works:** triggers `photo_expand_score` (tap to read) + `dwell_time` (time spent reading). Screenshots also share well via copy-link → `share_via_copy_link_score`.

**Anti-pattern:** text too small at thumbnail → reader doesn't realize there's text to read → no expand.

### Pattern 2 — Two-panel comparison

Two images stitched side-by-side (before/after, mine/theirs, A/B). Thumbnail shows there's a comparison; expand reveals the details.

**Why this works:** comparisons are inherently expand-worthy. The reader can't judge without seeing both sides clearly.

**Anti-pattern:** comparison that resolves at thumbnail size — no expand needed.

### Pattern 3 — Densely-annotated screenshot

A screenshot of code, a chart, or a UI with arrows / circles / numbered callouts pointing at specific elements.

**Why this works:** the annotations are the value, and they're only legible at full size. Expand rate is high. Often pairs with thread (each annotation becomes a tweet in the thread).

**Anti-pattern:** too many annotations — reader can't track them all.

### Pattern 4 — One striking photo with subtle weirdness

A photo where the thumbnail looks normal at first glance, but something in it makes the reader pause. They expand to confirm what they saw.

**Why this works:** drives `photo_expand_score` from curiosity. The pause itself raises `dwell_time`.

**Anti-pattern:** shock content — risks `NSFA_HIGH_PRECISION` / `NSFW_HIGH_PRECISION` labels (`home-mixer/filters/vf_filter.rs`), which can drop the post entirely.

### Pattern 5 — Chart with one outlier highlighted

A chart where one data point is visually emphasized (color, size, callout). Thumbnail shows the chart; expand lets the reader confirm the outlier.

**Why this works:** charts read well in copy-link previews, so they drive `share_via_copy_link_score` alongside `photo_expand_score`. The highlighted outlier gives readers a specific reason to engage (replies arguing about whether the outlier is real / matters).

**Anti-pattern:** unsourced chart — Community Note risk.

---

## Image dimensions and feed rendering

X displays images cropped to fit the feed aspect ratio by default. Composing for the crop matters:

- **Square (1:1)** — most defensive; shows most of the image in feed crop.
- **Landscape (16:9)** — taller crop, less visible at thumbnail.
- **Portrait (4:5 or 9:16)** — risks being cut off at top/bottom.

If the payoff is visual, prefer square or near-square. If you're posting a screenshot with text, ensure the key line is in the middle 60% so the crop doesn't hide it.

---

## Cadence

Image posts compete with each other for the same author-diversity decay. But images don't have the dwell-cost of long-form text or video, so you can post slightly more often than dwell or video posts. Still: ≥30 min between same-format posts is a safe floor.

## Multimodal embedding implication

`grox/embedder/multimodal_post_embedder_v5.py` and the v5 plans (`grox/plans/plan_post_embedding_v5.py`) generate joint embeddings of text + image. The image you choose shifts where your post lives in retrieval space. A post about "rust performance" with a chart of benchmarks will retrieve to viewers engaging with performance content; the same post text with a generic stock photo will retrieve more weakly. **Match the image to the post's intent.**

## Output contract (when invoked)

When the user asks you to draft an image post, return:

1. The chosen pattern.
2. The image description / composition brief.
3. The post text.
4. Why the image is worth expanding (the payoff at full size).
5. Risk flags: VF label risk (`vf_filter.rs`), Community Note risk for unsourced visuals.
