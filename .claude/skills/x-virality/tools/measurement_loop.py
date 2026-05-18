#!/usr/bin/env python3
"""Compare predicted vs actual engagement on a posted X post.

Workflow:
1. Before posting, the agent estimates Phoenix-like probabilities for each
   action (favorite, reply, retweet, share, dwell, follow_author, etc.).
2. After ~24 hours, the user provides the actual engagement counts from the
   X analytics dashboard (or via the X API in an automated context).
3. This script computes a per-signal hit/miss profile, flags large drifts,
   and writes a JSON log to `.claude/skills/x-virality/measurements/`.

The log accumulates over time. Running with `--summary` aggregates across
all logs to surface which signals the agent consistently over/under-predicts.

Usage:
    python ... measurement_loop.py record --predictions pred.json --actuals actual.json
    python ... measurement_loop.py summary
    python ... measurement_loop.py summary --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = SKILL_DIR / "measurements"

# Maps Phoenix prediction field → matching field name in X analytics.
# Both sides are agent-supplied dicts; this matches them up.
SIGNAL_MAP: dict[str, str] = {
    "favorite": "likes",
    "reply": "replies",
    "retweet": "retweets",
    "quote": "quotes",
    "share": "shares",
    "share_via_dm": "dm_shares",
    "share_via_copy_link": "copy_link_shares",
    "click": "url_clicks",
    "profile_click": "profile_visits",
    "photo_expand": "media_views",
    "vqv": "video_quality_views",
    "follow_author": "new_follows",
    "dwell_time": "dwell_seconds",
}

# Drift threshold (ratio between actual and predicted).
LARGE_DRIFT_LOG_FACTOR = 3.0


@dataclass
class SignalDrift:
    signal: str
    predicted: float
    actual: float

    @property
    def ratio(self) -> float | None:
        if self.predicted == 0:
            return None
        return self.actual / self.predicted

    @property
    def is_large(self) -> bool:
        r = self.ratio
        if r is None:
            return self.actual > 0  # predicted 0, got nonzero → drift
        return r >= LARGE_DRIFT_LOG_FACTOR or r <= (1 / LARGE_DRIFT_LOG_FACTOR)

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "predicted": self.predicted,
            "actual": self.actual,
            "ratio": self.ratio,
            "large_drift": self.is_large,
        }


@dataclass
class Measurement:
    post_id: str
    recorded_at: float
    drifts: list[SignalDrift] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "recorded_at": self.recorded_at,
            "drifts": [d.to_dict() for d in self.drifts],
            "notes": self.notes,
        }


def compare(
    predictions: dict[str, float],
    actuals: dict[str, float],
    signal_map: dict[str, str] = SIGNAL_MAP,
) -> list[SignalDrift]:
    """Align predictions to actuals via the signal map; return a drift per signal."""
    drifts: list[SignalDrift] = []
    for pred_key, actual_key in signal_map.items():
        if pred_key not in predictions and actual_key not in actuals:
            continue
        drifts.append(
            SignalDrift(
                signal=pred_key,
                predicted=float(predictions.get(pred_key, 0.0)),
                actual=float(actuals.get(actual_key, 0.0)),
            )
        )
    return drifts


def record(
    post_id: str,
    predictions: dict[str, float],
    actuals: dict[str, float],
    log_dir: Path = DEFAULT_LOG_DIR,
    notes: str = "",
    clock: callable = time.time,
) -> Measurement:
    """Compute drifts and persist to a JSON log."""
    log_dir.mkdir(parents=True, exist_ok=True)
    measurement = Measurement(
        post_id=post_id,
        recorded_at=clock(),
        drifts=compare(predictions, actuals),
        notes=notes,
    )
    log_path = log_dir / f"{post_id}.json"
    log_path.write_text(
        json.dumps(measurement.to_dict(), indent=2), encoding="utf-8"
    )
    return measurement


def load_all(log_dir: Path = DEFAULT_LOG_DIR) -> list[Measurement]:
    if not log_dir.exists():
        return []
    out: list[Measurement] = []
    for path in sorted(log_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append(
            Measurement(
                post_id=data["post_id"],
                recorded_at=data["recorded_at"],
                drifts=[
                    SignalDrift(
                        signal=d["signal"],
                        predicted=d["predicted"],
                        actual=d["actual"],
                    )
                    for d in data["drifts"]
                ],
                notes=data.get("notes", ""),
            )
        )
    return out


def summarize(measurements: Iterable[Measurement]) -> dict:
    """Aggregate which signals consistently over/under-predict."""
    by_signal: dict[str, list[SignalDrift]] = {}
    for m in measurements:
        for d in m.drifts:
            by_signal.setdefault(d.signal, []).append(d)

    summary = {}
    for signal, drifts in by_signal.items():
        ratios = [d.ratio for d in drifts if d.ratio is not None]
        if not ratios:
            summary[signal] = {"count": len(drifts), "avg_ratio": None,
                               "median_ratio": None}
            continue
        ratios_sorted = sorted(ratios)
        avg = sum(ratios) / len(ratios)
        med = ratios_sorted[len(ratios_sorted) // 2]
        summary[signal] = {
            "count": len(drifts),
            "avg_ratio": avg,
            "median_ratio": med,
            "over_predicting": avg < 1.0,  # predicted higher than actual
            "under_predicting": avg > 1.0,
        }
    return summary


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Measurement loop for x-virality predictions."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_record = sub.add_parser("record",
                              help="Record one post's predicted-vs-actual.")
    p_record.add_argument("--post-id", required=True)
    p_record.add_argument("--predictions", type=Path, required=True,
                          help="JSON file: {phoenix_field: probability}")
    p_record.add_argument("--actuals", type=Path, required=True,
                          help="JSON file: {analytics_field: count}")
    p_record.add_argument("--notes", default="")
    p_record.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)

    p_summary = sub.add_parser("summary",
                               help="Aggregate across all recorded posts.")
    p_summary.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    p_summary.add_argument("--json", dest="emit_json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "record":
        predictions = _load_json(args.predictions)
        actuals = _load_json(args.actuals)
        m = record(
            post_id=args.post_id,
            predictions=predictions,
            actuals=actuals,
            log_dir=args.log_dir,
            notes=args.notes,
        )
        print(json.dumps(m.to_dict(), indent=2))
        return 0

    if args.cmd == "summary":
        measurements = load_all(args.log_dir)
        summary = summarize(measurements)
        if args.emit_json:
            print(json.dumps({"posts": len(measurements),
                              "by_signal": summary}, indent=2))
            return 0
        print(f"Measurements: {len(measurements)} post(s) recorded.")
        print()
        for signal, stats in sorted(summary.items()):
            label = ""
            if stats.get("over_predicting"):
                label = "  (over-predicting)"
            elif stats.get("under_predicting"):
                label = "  (under-predicting)"
            print(f"  {signal:<20} n={stats['count']:<3} "
                  f"avg_ratio={stats['avg_ratio']}{label}")
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
