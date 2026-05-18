#!/usr/bin/env python3
"""Heuristic weighted-score simulator for X (For You) posts.

This is a Python re-implementation of the structure of:

    home-mixer/scorers/weighted_scorer.rs::compute_weighted_score
    home-mixer/scorers/ranking_scorer.rs::compute_weighted_score
    home-mixer/scorers/author_diversity_scorer.rs
    home-mixer/scorers/oon_scorer.rs

It is NOT a Phoenix clone. The Phoenix model outputs the per-action
probabilities; here we accept those as inputs (you supply them based on
your own judgement about a draft, or feed in historical engagement rates
for similar posts).

Why this is useful:
- Encodes the formula so the team can reason about trade-offs.
- Catches structural mistakes early (e.g. video below MinVideoDurationMs
  zeroing the VQV weight).
- Provides a sanity-check the skill stays consistent with the Rust code
  (the unit tests assert formula equivalence).

The numeric weights default to a balanced placeholder set documented in
``DEFAULT_WEIGHTS``. Real production weights are runtime params — pass
your own via the ``ScoringWeights`` dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

NEGATIVE_SCORES_OFFSET = 1.0
DEFAULT_MIN_VIDEO_DURATION_MS = 5_000  # 5 seconds


@dataclass(frozen=True)
class ScoringWeights:
    """Weight per predicted-action field.

    Mirrors home-mixer/scorers/ranking_scorer.rs::ScoringWeights. Positive
    actions have positive weights; negative actions have negative weights.

    Default values are illustrative ratios reflecting the prioritization
    discussed in references/scoring-weights.md. They are NOT production
    values. Override for your context.
    """

    favorite: float = 0.5
    reply: float = 13.5
    retweet: float = 1.0
    photo_expand: float = 0.1
    click: float = 0.1
    profile_click: float = 12.0
    vqv: float = 0.005
    share: float = 1.0
    share_via_dm: float = 1.0
    share_via_copy_link: float = 1.0
    dwell: float = 0.5
    quote: float = 1.0
    quoted_click: float = 1.0
    quoted_vqv: float = 0.005
    cont_dwell_time: float = 0.0001
    cont_click_dwell_time: float = 0.0001
    follow_author: float = 24.0
    not_interested: float = -8.0
    block_author: float = -80.0
    mute_author: float = -40.0
    report: float = -100.0
    not_dwelled: float = -0.5
    min_video_duration_ms: int = DEFAULT_MIN_VIDEO_DURATION_MS
    enable_quoted_vqv_duration_check: bool = True

    @property
    def positive_sum(self) -> float:
        """Sum of all positive-weight signal weights (mirrors Rust)."""
        return (
            self.favorite + self.reply + self.retweet + self.photo_expand
            + self.click + self.profile_click + self.vqv + self.share
            + self.share_via_dm + self.share_via_copy_link + self.dwell
            + self.quote + self.quoted_click + self.quoted_vqv
            + self.follow_author
        )

    @property
    def negative_sum(self) -> float:
        """Mirrors `negative_sum = -(not_interested + block + mute + report + not_dwelled)`."""
        return -(self.not_interested + self.block_author + self.mute_author
                 + self.report + self.not_dwelled)

    @property
    def total_sum(self) -> float:
        return self.positive_sum + self.negative_sum


@dataclass(frozen=True)
class PhoenixScores:
    """Per-action probability predictions (in [0, 1])."""

    favorite: float = 0.0
    reply: float = 0.0
    retweet: float = 0.0
    photo_expand: float = 0.0
    click: float = 0.0
    profile_click: float = 0.0
    vqv: float = 0.0
    share: float = 0.0
    share_via_dm: float = 0.0
    share_via_copy_link: float = 0.0
    dwell: float = 0.0
    quote: float = 0.0
    quoted_click: float = 0.0
    quoted_vqv: float = 0.0
    dwell_time: float = 0.0
    click_dwell_time: float = 0.0
    follow_author: float = 0.0
    not_interested: float = 0.0
    block_author: float = 0.0
    mute_author: float = 0.0
    report: float = 0.0
    not_dwelled: float = 0.0


@dataclass(frozen=True)
class Candidate:
    """A single post being scored."""

    scores: PhoenixScores
    in_network: bool = True
    video_duration_ms: int | None = None
    quoted_video_duration_ms: int | None = None
    author_id: int = 0


def vqv_weight(candidate: Candidate, weights: ScoringWeights) -> float:
    """Mirrors `weighted_scorer.rs::vqv_weight_eligibility`."""
    if (candidate.video_duration_ms is not None
            and candidate.video_duration_ms > weights.min_video_duration_ms):
        return weights.vqv
    return 0.0


def quoted_vqv_weight(candidate: Candidate, weights: ScoringWeights) -> float:
    """Mirrors the quoted-vqv gating in `ranking_scorer.rs`."""
    if not weights.enable_quoted_vqv_duration_check:
        return weights.quoted_vqv
    if (candidate.quoted_video_duration_ms is not None
            and candidate.quoted_video_duration_ms > weights.min_video_duration_ms):
        return weights.quoted_vqv
    return 0.0


def compute_weighted_score(candidate: Candidate, weights: ScoringWeights) -> float:
    """Sum of (score × weight) over all action fields, before offset."""
    s = candidate.scores
    return (
        s.favorite * weights.favorite
        + s.reply * weights.reply
        + s.retweet * weights.retweet
        + s.photo_expand * weights.photo_expand
        + s.click * weights.click
        + s.profile_click * weights.profile_click
        + s.vqv * vqv_weight(candidate, weights)
        + s.share * weights.share
        + s.share_via_dm * weights.share_via_dm
        + s.share_via_copy_link * weights.share_via_copy_link
        + s.dwell * weights.dwell
        + s.quote * weights.quote
        + s.quoted_click * weights.quoted_click
        + s.quoted_vqv * quoted_vqv_weight(candidate, weights)
        + s.dwell_time * weights.cont_dwell_time
        + s.click_dwell_time * weights.cont_click_dwell_time
        + s.follow_author * weights.follow_author
        + s.not_interested * weights.not_interested
        + s.block_author * weights.block_author
        + s.mute_author * weights.mute_author
        + s.report * weights.report
        + s.not_dwelled * weights.not_dwelled
    )


def offset_score(combined: float, weights: ScoringWeights,
                 negative_offset: float = NEGATIVE_SCORES_OFFSET) -> float:
    """Mirrors `weighted_scorer.rs::offset_score` and `ranking_scorer.rs::offset_score`."""
    if weights.total_sum == 0.0:
        return max(combined, 0.0)
    if combined < 0.0:
        return (combined + weights.negative_sum) / weights.total_sum * negative_offset
    return combined + negative_offset


def diversity_multiplier(position: int, decay: float, floor: float) -> float:
    """Mirrors `author_diversity_scorer.rs::multiplier` and `ranking_scorer.rs::diversity_multiplier`."""
    return (1.0 - floor) * (decay ** position) + floor


def apply_author_diversity(candidates: list[Candidate], weighted: list[float],
                           decay: float, floor: float) -> list[float]:
    """Mirrors `ranking_scorer.rs::apply_author_diversity`.

    The Nth post from a given author (when sorted by descending weighted
    score) gets multiplied by ``diversity_multiplier(N, decay, floor)``.
    """
    indexed = sorted(enumerate(weighted), key=lambda x: x[1], reverse=True)
    author_counts: dict[int, int] = {}
    adjusted = [0.0] * len(candidates)
    for original_idx, w in indexed:
        author = candidates[original_idx].author_id
        pos = author_counts.get(author, 0)
        author_counts[author] = pos + 1
        adjusted[original_idx] = w * diversity_multiplier(pos, decay, floor)
    return adjusted


def apply_oon(candidates: list[Candidate], adjusted: list[float],
              oon_factor: float) -> list[float]:
    """Mirrors `oon_scorer.rs`: multiply OON candidates by `oon_factor`."""
    return [
        score * oon_factor if not c.in_network else score
        for c, score in zip(candidates, adjusted)
    ]


@dataclass(frozen=True)
class ScoreReport:
    """Full pipeline output for one candidate, for inspection."""

    candidate: Candidate
    combined: float
    offset: float
    diversity_adjusted: float
    final: float
    vqv_eligible: bool
    quoted_vqv_eligible: bool

    def explain(self) -> str:
        lines = [
            f"in_network={self.candidate.in_network}",
            f"video_duration_ms={self.candidate.video_duration_ms} "
            f"(vqv_eligible={self.vqv_eligible})",
            f"combined_weighted_score={self.combined:.4f}",
            f"offset_score={self.offset:.4f}",
            f"after_diversity={self.diversity_adjusted:.4f}",
            f"final={self.final:.4f}",
        ]
        return "\n".join(lines)


def score_batch(
    candidates: Iterable[Candidate],
    weights: ScoringWeights = ScoringWeights(),
    *,
    diversity_decay: float = 0.7,
    diversity_floor: float = 0.3,
    oon_factor: float = 0.5,
) -> list[ScoreReport]:
    """Score a batch of candidates end-to-end and return per-candidate reports.

    Defaults for ``diversity_decay``, ``diversity_floor``, ``oon_factor`` are
    illustrative. Override for your context.
    """
    cands = list(candidates)
    combined = [compute_weighted_score(c, weights) for c in cands]
    offset = [offset_score(c, weights) for c in combined]
    diversity = apply_author_diversity(cands, offset, diversity_decay, diversity_floor)
    final = apply_oon(cands, diversity, oon_factor)

    return [
        ScoreReport(
            candidate=cand,
            combined=combined[i],
            offset=offset[i],
            diversity_adjusted=diversity[i],
            final=final[i],
            vqv_eligible=vqv_weight(cand, weights) > 0.0,
            quoted_vqv_eligible=quoted_vqv_weight(cand, weights) > 0.0,
        )
        for i, cand in enumerate(cands)
    ]


__all__ = [
    "DEFAULT_MIN_VIDEO_DURATION_MS",
    "NEGATIVE_SCORES_OFFSET",
    "Candidate",
    "PhoenixScores",
    "ScoreReport",
    "ScoringWeights",
    "apply_author_diversity",
    "apply_oon",
    "compute_weighted_score",
    "diversity_multiplier",
    "offset_score",
    "quoted_vqv_weight",
    "score_batch",
    "vqv_weight",
]
