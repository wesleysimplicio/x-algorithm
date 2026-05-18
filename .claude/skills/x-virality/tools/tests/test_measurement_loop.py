"""Tests for the prediction-vs-actual measurement loop."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import measurement_loop as ml


# ---------------------------------------------------------------------------
# compare()
# ---------------------------------------------------------------------------


def test_compare_returns_one_drift_per_signal_present():
    predictions = {"favorite": 0.1, "reply": 0.05}
    actuals = {"likes": 12, "replies": 3}
    drifts = ml.compare(predictions, actuals)
    by_signal = {d.signal: d for d in drifts}
    assert by_signal["favorite"].predicted == 0.1
    assert by_signal["favorite"].actual == 12
    assert by_signal["reply"].actual == 3


def test_compare_skips_signals_absent_on_both_sides():
    drifts = ml.compare({"favorite": 0.1}, {"likes": 5})
    signals = {d.signal for d in drifts}
    # Only "favorite" was present; nothing else should be returned.
    assert signals == {"favorite"}


def test_compare_handles_zero_predicted():
    drifts = ml.compare({"favorite": 0}, {"likes": 10})
    drift = drifts[0]
    assert drift.predicted == 0
    assert drift.actual == 10
    assert drift.ratio is None


def test_drift_ratio_basic():
    drift = ml.SignalDrift(signal="reply", predicted=0.5, actual=5.0)
    assert drift.ratio == pytest.approx(10.0)


def test_drift_is_large_when_ratio_exceeds_threshold():
    over = ml.SignalDrift(signal="x", predicted=1.0, actual=5.0)
    under = ml.SignalDrift(signal="x", predicted=5.0, actual=1.0)
    normal = ml.SignalDrift(signal="x", predicted=1.0, actual=1.5)
    assert over.is_large is True
    assert under.is_large is True
    assert normal.is_large is False


def test_drift_is_large_when_predicted_zero_actual_nonzero():
    d = ml.SignalDrift(signal="x", predicted=0, actual=5)
    assert d.is_large is True


def test_drift_is_not_large_when_both_zero():
    d = ml.SignalDrift(signal="x", predicted=0, actual=0)
    assert d.is_large is False


# ---------------------------------------------------------------------------
# record() persists to disk
# ---------------------------------------------------------------------------


def test_record_writes_log_file(tmp_path: Path):
    measurement = ml.record(
        post_id="1234",
        predictions={"reply": 0.1, "favorite": 0.3},
        actuals={"replies": 5, "likes": 50},
        log_dir=tmp_path,
        clock=lambda: 1700000000.0,
    )
    assert measurement.post_id == "1234"
    assert measurement.recorded_at == 1700000000.0
    log_file = tmp_path / "1234.json"
    assert log_file.exists()
    data = json.loads(log_file.read_text())
    assert data["post_id"] == "1234"
    signals = {d["signal"] for d in data["drifts"]}
    assert signals == {"reply", "favorite"}


def test_record_includes_notes(tmp_path: Path):
    ml.record(
        post_id="9",
        predictions={"reply": 0.1},
        actuals={"replies": 1},
        log_dir=tmp_path,
        notes="first attempt",
        clock=lambda: 0.0,
    )
    data = json.loads((tmp_path / "9.json").read_text())
    assert data["notes"] == "first attempt"


# ---------------------------------------------------------------------------
# load_all() + summarize()
# ---------------------------------------------------------------------------


def test_load_all_returns_empty_when_dir_missing(tmp_path: Path):
    missing = tmp_path / "does_not_exist"
    assert ml.load_all(missing) == []


def test_load_all_round_trips(tmp_path: Path):
    ml.record(
        post_id="a", predictions={"reply": 0.1}, actuals={"replies": 1},
        log_dir=tmp_path, clock=lambda: 1.0,
    )
    ml.record(
        post_id="b", predictions={"reply": 0.2}, actuals={"replies": 4},
        log_dir=tmp_path, clock=lambda: 2.0,
    )
    measurements = ml.load_all(tmp_path)
    assert len(measurements) == 2
    ids = {m.post_id for m in measurements}
    assert ids == {"a", "b"}


def test_summarize_reports_average_ratio():
    measurements = [
        ml.Measurement(
            post_id="1", recorded_at=0,
            drifts=[ml.SignalDrift("reply", predicted=1.0, actual=2.0)],
        ),
        ml.Measurement(
            post_id="2", recorded_at=0,
            drifts=[ml.SignalDrift("reply", predicted=1.0, actual=4.0)],
        ),
    ]
    summary = ml.summarize(measurements)
    assert summary["reply"]["count"] == 2
    assert summary["reply"]["avg_ratio"] == pytest.approx(3.0)
    # Avg ratio > 1 = predicted lower than actual = under-predicting.
    assert summary["reply"]["under_predicting"] is True


def test_summarize_handles_over_prediction():
    measurements = [
        ml.Measurement(
            post_id="1", recorded_at=0,
            drifts=[ml.SignalDrift("reply", predicted=10.0, actual=2.0)],
        ),
    ]
    summary = ml.summarize(measurements)
    assert summary["reply"]["over_predicting"] is True


def test_summarize_handles_zero_predicted_skip():
    measurements = [
        ml.Measurement(
            post_id="1", recorded_at=0,
            drifts=[ml.SignalDrift("reply", predicted=0.0, actual=5.0)],
        ),
    ]
    summary = ml.summarize(measurements)
    assert summary["reply"]["count"] == 1
    assert summary["reply"]["avg_ratio"] is None


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_record_then_summary(tmp_path: Path, capsys):
    pred_path = tmp_path / "pred.json"
    actual_path = tmp_path / "actual.json"
    pred_path.write_text(json.dumps({"reply": 0.1, "favorite": 0.4}))
    actual_path.write_text(json.dumps({"replies": 5, "likes": 80}))
    log_dir = tmp_path / "logs"

    rc = ml.main([
        "record", "--post-id", "42",
        "--predictions", str(pred_path),
        "--actuals", str(actual_path),
        "--log-dir", str(log_dir),
    ])
    assert rc == 0
    # Drain stdout from the record call before invoking summary.
    capsys.readouterr()

    rc2 = ml.main([
        "summary",
        "--log-dir", str(log_dir),
        "--json",
    ])
    assert rc2 == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["posts"] == 1
    assert "reply" in data["by_signal"]
    assert "favorite" in data["by_signal"]
