# Multimodal Playbook

The Grox content-understanding pipeline produces joint embeddings of text + media for every post. Those embeddings feed Phoenix retrieval (`phoenix/recsys_retrieval_model.py`), so what your media looks like changes which viewers your post is retrievable for, not just whether they engage.

Source:
- `grox/embedder/multimodal_post_embedder_v5.py` — the v5 multimodal embedder.
- `grox/plans/plan_post_embedding_v5.py` — the v5 embedding plan for original posts.
- `grox/plans/plan_post_embedding_v5_for_reply.py` — variant for replies.
- `grox/plans/plan_post_embedding_with_summary.py` — variant that includes a Grok-generated summary.
- `grox/summarizer/post_embedding_summarizer.py` — the summarizer that feeds the embedding.
- `grox/tasks/task_multimodal_post_embedding.py` — the task that runs it.

---

## Why this matters

The retrieval stage (`phoenix/run_retrieval.py`, `phoenix/recsys_retrieval_model.py`) finds out-of-network candidates by similarity search over post embeddings. Your post's embedding determines:

1. Which viewers' user-tower embeddings have high dot-product similarity with your post.
2. Whether your post even appears in their candidate set.

Without retrieval finding you, the ranking weights don't matter — your post isn't a candidate to rank.

The Grox multimodal embedder fuses text + image (and possibly audio via `grox/data_loaders/asr_processor.py`) into one representation. So:

- **Text-only post:** embedding is purely text-driven.
- **Image-paired post:** embedding shifts toward the visual content.
- **Video-paired post:** embedding incorporates frames + ASR transcript.

---

## Alignment patterns

### Pattern 1 — Text and media reinforce the same topic

The post text and the image (or video subject) talk about the same thing. The joint embedding is concentrated, retrieves strongly to viewers in that topic.

**Example:** post about Rust benchmarks + chart of Rust benchmarks.

**Why this works:** retrieval picks up both signals consistently. Viewers who like Rust performance content get a strong similarity score.

### Pattern 2 — Text and media create deliberate juxtaposition

The text frames the image as a contrast or counter-example. The embedding sits in between, retrieving to viewers in either neighborhood.

**Example:** post about a software bug + screenshot of the visually-impressive UI that has the bug.

**Why this works:** broader retrieval surface — your post is reachable from two adjacent neighborhoods. Useful when you want OON expansion without losing topic relevance.

**Anti-pattern:** juxtaposition without a verbal bridge — embedding becomes diffuse, retrieves weakly to anyone.

### Pattern 3 — Media as evidence for a text claim

The text makes a claim, the image is the proof. Embedding stays close to the claim's topic.

**Example:** "ACME's UI broke this week" + screenshot of the broken UI.

**Why this works:** claim + evidence is highly engaging — drives `dwell_score`, `reply_score`, `photo_expand_score`. The embedding stays tight.

---

## Anti-patterns

### Pure decoration

Posting text with a tangentially-related stock image diffuses the embedding. The image pulls the representation toward "generic visual" while the text is specific. You retrieve worse than text alone would have.

**Better:** drop the decorative image. Text-only is fine.

### Mismatched languages / tone

If your text is technical and your image is a meme reaction shot, the embedding lands somewhere weird. Retrieval to either audience is weakened.

**Better:** match tone or commit fully to the contrast (Pattern 2).

### Auto-generated visuals from outside the post's topic

AI image generators tend to produce decorative-but-generic visuals. These push your embedding toward "AI-art neighborhood" rather than your topic.

**Better:** generate visuals specifically relevant, or use a chart / screenshot grounded in real content.

---

## Reply embeddings

Replies have their own embedding plan (`grox/plans/plan_post_embedding_v5_for_reply.py`). Reply ranking happens via `plan_reply_ranking.py`. The reply's embedding is influenced by the parent post — so a reply quoting the parent's key term has a stronger representation than a generic "agreed" reply.

For your own replies on others' viral posts:
- Reference the parent's specific framing in your reply.
- Add value (data, counter, refinement) — embeddings of valueless replies cluster with low-engagement replies and rank poorly.

---

## Summarization variant

`grox/plans/plan_post_embedding_with_summary.py` and `plan_post_embedding_with_summary_for_reply.py` use a Grok-generated summary as additional input to the embedding. For long-form posts, the summary captures the gist for retrieval purposes.

**Implication for writers:** your post's first paragraph or "thesis line" disproportionately influences the summary the embedder receives. Lead with the strongest summary-worthy claim, even if the rest of the post elaborates.

---

## Output contract (when invoked)

When the user asks you to design a multimodal post (text + media), return:

1. The chosen alignment pattern (reinforcement / juxtaposition / evidence).
2. The text content.
3. The media brief: what the image / video should depict, and why it aligns with the text's topic.
4. Retrieval intent: which viewer neighborhoods you want this to retrieve to.
5. Risk flags: anti-pattern check (decoration, mismatch, generic AI art).
