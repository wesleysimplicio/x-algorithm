"""Unit + regression tests for the x-virality score simulator.

These tests pin the structure of the scoring formula to the Rust source.
If the production code changes shape (new positive/negative action, new
gating, different offset semantics), these tests fail loudly and tell us
to update both the simulator and the skill docs.
"""
from __future__ import annotations

import math

import pytest

import score_simulator as ss


# ---------------------------------------------------------------------------
# vqv gating
# ---------------------------------------------------------------------------


def test_vqv_weight_zero_when_no_video():
    cand = ss.Candidate(scores=ss.PhoenixScores(vqv=1.0), video_duration_ms=None)
    assert ss.vqv_weight(cand, ss.ScoringWeights()) == 0.0


def test_vqv_weight_zero_when_below_threshold():
    weights = ss.ScoringWeights(min_video_duration_ms=5_000)
    cand = ss.Candidate(scores=ss.PhoenixScores(vqv=1.0), video_duration_ms=4_999)
    assert ss.vqv_weight(cand, weights) == 0.0


def test_vqv_weight_active_when_above_threshold():
    weights = ss.ScoringWeights(min_video_duration_ms=5_000, vqv=0.42)
    cand = ss.Candidate(scores=ss.PhoenixScores(vqv=1.0), video_duration_ms=5_001)
    assert ss.vqv_weight(cand, weights) == 0.42


def test_vqv_weight_exactly_threshold_is_excluded():
    """The Rust code uses `> MinVideoDurationMs`, not `>=`."""
    weights = ss.ScoringWeights(min_video_duration_ms=5_000, vqv=0.42)
    cand = ss.Candidate(scores=ss.PhoenixScores(vqv=1.0), video_duration_ms=5_000)
    assert ss.vqv_weight(cand, weights) == 0.0


def test_quoted_vqv_gating_can_be_disabled():
    weights = ss.ScoringWeights(enable_quoted_vqv_duration_check=False, quoted_vqv=0.5)
    cand = ss.Candidate(scores=ss.PhoenixScores(quoted_vqv=1.0), quoted_video_duration_ms=None)
    assert ss.quoted_vqv_weight(cand, weights) == 0.5


def test_quoted_vqv_gating_when_enabled_respects_threshold():
    weights = ss.ScoringWeights(
        enable_quoted_vqv_duration_check=True,
        quoted_vqv=0.5,
        min_video_duration_ms=5_000,
    )
    low = ss.Candidate(scores=ss.PhoenixScores(quoted_vqv=1.0), quoted_video_duration_ms=1_000)
    high = ss.Candidate(scores=ss.PhoenixScores(quoted_vqv=1.0), quoted_video_duration_ms=6_000)
    assert ss.quoted_vqv_weight(low, weights) == 0.0
    assert ss.quoted_vqv_weight(high, weights) == 0.5


# ---------------------------------------------------------------------------
# compute_weighted_score
# ---------------------------------------------------------------------------


def test_combined_score_is_linear_in_each_field():
    weights = ss.ScoringWeights(favorite=2.0, reply=3.0)
    a = ss.Candidate(scores=ss.PhoenixScores(favorite=1.0))
    b = ss.Candidate(scores=ss.PhoenixScores(reply=1.0))
    both = ss.Candidate(scores=ss.PhoenixScores(favorite=1.0, reply=1.0))
    assert ss.compute_weighted_score(a, weights) == 2.0
    assert ss.compute_weighted_score(b, weights) == 3.0
    assert ss.compute_weighted_score(both, weights) == 5.0


def test_zero_scores_zero_out():
    weights = ss.ScoringWeights()
    cand = ss.Candidate(scores=ss.PhoenixScores())
    assert ss.compute_weighted_score(cand, weights) == 0.0


def test_negative_signals_push_score_negative():
    weights = ss.ScoringWeights(favorite=1.0, report=-100.0)
    cand = ss.Candidate(scores=ss.PhoenixScores(favorite=0.1, report=0.1))
    expected = 0.1 * 1.0 + 0.1 * -100.0
    assert ss.compute_weighted_score(cand, weights) == pytest.approx(expected)


def test_follow_outweighs_favorite_at_default_weights():
    """Defaults encode the prioritization documented in scoring-weights.md.

    Earning a follow is worth more than earning a like at the same predicted
    probability. If this regresses, we're misrepresenting the algorithm.
    """
    w = ss.ScoringWeights()
    like_only = ss.Candidate(scores=ss.PhoenixScores(favorite=1.0))
    follow_only = ss.Candidate(scores=ss.PhoenixScores(follow_author=1.0))
    assert (
        ss.compute_weighted_score(follow_only, w)
        > ss.compute_weighted_score(like_only, w)
    )


def test_reply_outweighs_favorite_at_default_weights():
    w = ss.ScoringWeights()
    like_only = ss.Candidate(scores=ss.PhoenixScores(favorite=1.0))
    reply_only = ss.Candidate(scores=ss.PhoenixScores(reply=1.0))
    assert (
        ss.compute_weighted_score(reply_only, w)
        > ss.compute_weighted_score(like_only, w)
    )


# ---------------------------------------------------------------------------
# offset_score
# ---------------------------------------------------------------------------


def test_offset_when_total_sum_zero_clamps_to_zero():
    """When `total_sum == 0`, the Rust code returns `max(combined, 0)`."""
    w = ss.ScoringWeights(
        favorite=0, reply=0, retweet=0, photo_expand=0, click=0,
        profile_click=0, vqv=0, share=0, share_via_dm=0,
        share_via_copy_link=0, dwell=0, quote=0, quoted_click=0,
        quoted_vqv=0, follow_author=0,
        not_interested=0, block_author=0, mute_author=0, report=0,
        not_dwelled=0,
    )
    assert w.total_sum == 0.0
    assert ss.offset_score(-1.0, w) == 0.0
    assert ss.offset_score(3.0, w) == 3.0


def test_offset_positive_combined_adds_offset():
    w = ss.ScoringWeights()
    assert (
        ss.offset_score(2.0, w, negative_offset=1.0)
        == pytest.approx(2.0 + 1.0)
    )


def test_offset_negative_combined_normalizes_via_negative_sum():
    """For combined < 0, the formula is:
        (combined + negative_sum) / total_sum * NEGATIVE_SCORES_OFFSET
    """
    w = ss.ScoringWeights()
    combined = -0.5
    expected = (combined + w.negative_sum) / w.total_sum * 1.0
    assert ss.offset_score(combined, w, negative_offset=1.0) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# diversity decay
# ---------------------------------------------------------------------------


def test_diversity_multiplier_at_position_zero_is_one():
    assert ss.diversity_multiplier(0, decay=0.5, floor=0.2) == pytest.approx(1.0)


def test_diversity_multiplier_decays_toward_floor():
    floor = 0.25
    decay = 0.5
    values = [ss.diversity_multiplier(p, decay, floor) for p in range(10)]
    # Monotone decreasing.
    for a, b in zip(values, values[1:]):
        assert b < a or math.isclose(b, a)
    # Asymptote toward floor.
    assert values[-1] >= floor
    assert values[-1] - floor < 0.01


def test_apply_author_diversity_penalizes_repeats():
    cand_high = ss.Candidate(scores=ss.PhoenixScores(), author_id=1)
    cand_mid = ss.Candidate(scores=ss.PhoenixScores(), author_id=1)
    cand_other = ss.Candidate(scores=ss.PhoenixScores(), author_id=2)
    weighted = [10.0, 5.0, 7.0]
    adjusted = ss.apply_author_diversity(
        [cand_high, cand_mid, cand_other], weighted,
        decay=0.5, floor=0.0,
    )
    # The top-ranked of author 1 keeps full weight; the lower-ranked one
    # gets multiplied by 0.5.
    assert adjusted[0] == pytest.approx(10.0)
    assert adjusted[1] == pytest.approx(5.0 * 0.5)
    # Author 2 is at position 0 in its own bucket, untouched.
    assert adjusted[2] == pytest.approx(7.0)


def test_apply_author_diversity_ranking_uses_weighted_not_index():
    """The decay applies to the sort order by weighted score, not list order."""
    a_low = ss.Candidate(scores=ss.PhoenixScores(), author_id=1)
    a_high = ss.Candidate(scores=ss.PhoenixScores(), author_id=1)
    weighted = [1.0, 10.0]  # second post has higher score
    adjusted = ss.apply_author_diversity(
        [a_low, a_high], weighted, decay=0.5, floor=0.0,
    )
    # The high-scored one keeps full weight; the low-scored one decays.
    assert adjusted[1] == pytest.approx(10.0)
    assert adjusted[0] == pytest.approx(1.0 * 0.5)


# ---------------------------------------------------------------------------
# OON factor
# ---------------------------------------------------------------------------


def test_oon_factor_applied_only_to_oon_candidates():
    in_net = ss.Candidate(scores=ss.PhoenixScores(), in_network=True)
    oon = ss.Candidate(scores=ss.PhoenixScores(), in_network=False)
    adjusted = ss.apply_oon([in_net, oon], [10.0, 10.0], oon_factor=0.4)
    assert adjusted == [10.0, 10.0 * 0.4]


def test_oon_factor_one_is_a_noop():
    cands = [
        ss.Candidate(scores=ss.PhoenixScores(), in_network=True),
        ss.Candidate(scores=ss.PhoenixScores(), in_network=False),
    ]
    assert ss.apply_oon(cands, [3.0, 7.0], oon_factor=1.0) == [3.0, 7.0]


# ---------------------------------------------------------------------------
# score_batch end-to-end
# ---------------------------------------------------------------------------


def test_score_batch_returns_one_report_per_candidate():
    candidates = [
        ss.Candidate(scores=ss.PhoenixScores(favorite=0.1)),
        ss.Candidate(scores=ss.PhoenixScores(reply=0.1)),
    ]
    reports = ss.score_batch(candidates)
    assert len(reports) == 2
    assert all(isinstance(r, ss.ScoreReport) for r in reports)


def test_score_batch_oon_post_loses_to_in_network_post_with_same_scores():
    """OON factor < 1 means an equivalent OON post should rank lower."""
    base = ss.PhoenixScores(reply=0.2, favorite=0.3, dwell=0.4)
    in_net = ss.Candidate(scores=base, in_network=True, author_id=1)
    oon = ss.Candidate(scores=base, in_network=False, author_id=2)
    reports = ss.score_batch([in_net, oon], oon_factor=0.5)
    assert reports[0].final > reports[1].final


def test_score_batch_video_below_threshold_zeros_vqv_contribution():
    weights = ss.ScoringWeights(vqv=10.0, min_video_duration_ms=5_000)
    high_vqv_short = ss.Candidate(
        scores=ss.PhoenixScores(vqv=1.0),
        video_duration_ms=2_000,
        author_id=1,
    )
    high_vqv_long = ss.Candidate(
        scores=ss.PhoenixScores(vqv=1.0),
        video_duration_ms=10_000,
        author_id=2,
    )
    reports = ss.score_batch([high_vqv_short, high_vqv_long], weights=weights)
    assert reports[0].vqv_eligible is False
    assert reports[1].vqv_eligible is True
    assert reports[1].combined > reports[0].combined


def test_score_batch_diversity_penalizes_repeated_author():
    base = ss.PhoenixScores(reply=0.3)
    a1 = ss.Candidate(scores=base, author_id=42)
    a2 = ss.Candidate(scores=base, author_id=42)
    other = ss.Candidate(scores=base, author_id=99)
    reports = ss.score_batch(
        [a1, a2, other], diversity_decay=0.5, diversity_floor=0.0,
    )
    # Author 42 appears twice — the second occurrence is penalized.
    a_finals = sorted([reports[0].final, reports[1].final], reverse=True)
    assert a_finals[1] < a_finals[0]
    # The non-repeated author isn't penalized.
    assert reports[2].final == pytest.approx(a_finals[0])


# ---------------------------------------------------------------------------
# ScoringWeights structural invariants
# ---------------------------------------------------------------------------


def test_default_weights_have_expected_sign_structure():
    """Pins the sign of every weight field to its Rust counterpart.

    If you flip a sign here, you're misrepresenting the algorithm. This
    test exists to catch that.
    """
    w = ss.ScoringWeights()
    positives = [
        "favorite", "reply", "retweet", "photo_expand", "click",
        "profile_click", "vqv", "share", "share_via_dm",
        "share_via_copy_link", "dwell", "quote", "quoted_click",
        "quoted_vqv", "cont_dwell_time", "cont_click_dwell_time",
        "follow_author",
    ]
    negatives = ["not_interested", "block_author", "mute_author", "report",
                 "not_dwelled"]
    for name in positives:
        assert getattr(w, name) >= 0.0, f"{name} should be non-negative"
    for name in negatives:
        assert getattr(w, name) <= 0.0, f"{name} should be non-positive"


def test_negative_sum_is_positive_magnitude():
    """`negative_sum = -(sum of negative-weight fields)` → should be ≥ 0."""
    w = ss.ScoringWeights()
    assert w.negative_sum >= 0.0


def test_total_sum_is_positive_plus_negative():
    w = ss.ScoringWeights()
    assert w.total_sum == pytest.approx(w.positive_sum + w.negative_sum)
