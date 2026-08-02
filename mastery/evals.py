"""Score trending and baselines. STOP 7, parts 3 and 4.

A score on its own says very little. Two things make it mean something:

  - **Anchored rubric levels**, which live in `quality_rubrics.md` and make a
    single number interpretable without any reference run.
  - **A stored baseline**, here, which makes drift detectable and is what STOP 6's
    tiering gets measured against.

The baseline is keyed by `(agent, rubric_version, model)`, and all three parts are
load-bearing:

  - `agent`, because a global average across roles hides a role that got worse.
  - `rubric_version`, because changing a dimension or an anchor makes prior scores
    incomparable. Mixing versions in one trend shows a fake regression, or hides a
    real one.
  - `model`, because a baseline captured on one model says nothing about a run on
    another. This is the whole point of the exercise: STOP 6 tiers a role down and
    the tiered run must be compared against a baseline from the *stronger* model,
    like for like. Comparing a cheap run to a cheap baseline would show no
    regression no matter how much quality was lost.

`mastery eval` therefore refuses to group across mixed `rubric_version` or mixed
`model` rather than averaging them. An average across incomparable runs is worse
than no number, because it looks like a number.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import calibration
from .config import REPO_ROOT
from .runlog import RunLog

BASELINES_PATH = REPO_ROOT / "evals" / "baselines.json"


class IncomparableScores(Exception):
    """Refusing to aggregate scores that are not like for like."""


@dataclass(frozen=True)
class ScoreKey:
    agent: str
    rubric_version: str
    model: str

    def __str__(self) -> str:
        return f"{self.agent} (rubric v{self.rubric_version}, {self.model or 'unknown model'})"


@dataclass(frozen=True)
class ScoreRecord:
    key: ScoreKey
    task_id: str
    run_id: str
    ts: str
    overall: float
    normalised: float
    dimensions: dict
    cost_usd: float | None


def load_scores(log_dir: Path) -> list[ScoreRecord]:
    """Every `quality_score` event across every run log, newest last."""
    records: list[ScoreRecord] = []
    for path in sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
        for rec in RunLog(path=path, run_id=path.stem).read():
            if rec.get("event") != "quality_score":
                continue
            records.append(
                ScoreRecord(
                    key=ScoreKey(
                        agent=rec.get("agent", ""),
                        rubric_version=rec.get("rubric_version", ""),
                        model=rec.get("model", ""),
                    ),
                    task_id=rec.get("task_id", ""),
                    run_id=rec.get("run_id", ""),
                    ts=rec.get("ts", ""),
                    overall=rec.get("overall", 0.0),
                    normalised=rec.get("normalised", 0.0),
                    dimensions={
                        d["dimension"]: d["score"]
                        for d in rec.get("dimension_scores", [])
                    },
                    cost_usd=rec.get("cost_usd"),
                )
            )
    return records


def load_skips(log_dir: Path) -> list[dict]:
    """Every `quality_skipped` event — the visible holes in the trend."""
    out = []
    for path in sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
        for rec in RunLog(path=path, run_id=path.stem).read():
            if rec.get("event") == "quality_skipped":
                out.append(rec)
    return out


def group(records: list[ScoreRecord]) -> dict[ScoreKey, list[ScoreRecord]]:
    """Group by the full triple. Never by agent alone."""
    out: dict[ScoreKey, list[ScoreRecord]] = defaultdict(list)
    for r in records:
        out[r.key].append(r)
    return dict(out)


def check_comparable(records: list[ScoreRecord]) -> None:
    """Raise unless every record shares one rubric_version and one model.

    Called before anything averages a set of scores. This is the guard that makes
    a trend trustworthy: without it, `mastery eval` would happily average a
    strong-model run against a cheap-model run and report the mean as if it meant
    something.
    """
    versions = {r.key.rubric_version for r in records}
    models = {r.key.model for r in records}
    if len(versions) > 1:
        raise IncomparableScores(
            f"scores span rubric versions {sorted(versions)}. A changed rubric makes "
            f"prior scores incomparable; they cannot be averaged together."
        )
    if len(models) > 1:
        raise IncomparableScores(
            f"scores span models {sorted(models)}. A baseline on one model says "
            f"nothing about a run on another — comparing them is the mistake STOP 6 "
            f"exists to avoid."
        )


def trend(records: list[ScoreRecord]) -> list[tuple[str, float]]:
    """(timestamp, overall) in run order, for one comparable group."""
    check_comparable(records)
    return [(r.ts, r.overall) for r in records]


# -- baselines --------------------------------------------------------------


def load_baselines(path: Path = BASELINES_PATH) -> dict:
    if not path.exists():
        return {"_note": "written by `mastery eval --set-baseline`", "baselines": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_key(key: ScoreKey) -> str:
    return f"{key.agent}|{key.rubric_version}|{key.model}"


def set_baseline(
    records: list[ScoreRecord],
    *,
    label: str,
    path: Path = BASELINES_PATH,
    calibration_path: Path | None = None,
) -> dict:
    """Record a baseline from a comparable set of scores.

    `label` distinguishes what the numbers are. Ours are `fresh-strong-model` (the
    real baseline) and `retro-sanity-check` (grading of pre-eval runs, which is
    NOT a baseline). They are stored separately and never averaged: if they
    diverge, that divergence is information, and averaging it away would destroy
    the finding.

    **Refuses unless the rubric is calibrated for this exact version.** A baseline
    is the artifact that gets trusted — it is what STOP 6's tiering is measured
    against — and one drawn through an instrument of unknown resolution is a
    figure that looks like evidence without being any. Same principle as
    `check_comparable` directly above: refuse rather than emit a number whose
    meaning is undetermined. Scoring itself is not blocked by this; only the
    promotion of scores into a baseline. See `mastery/calibration.py`.
    """
    check_comparable(records)
    key = records[0].key
    calibration.require_calibrated(
        key.agent, key.rubric_version, path=calibration_path or calibration.RESULTS_PATH
    )
    data = load_baselines(path)
    data.setdefault("baselines", {})

    per_dimension: dict[str, list[int]] = defaultdict(list)
    for r in records:
        for dim, score in r.dimensions.items():
            per_dimension[dim].append(score)

    entry = {
        "agent": key.agent,
        "rubric_version": key.rubric_version,
        "model": key.model,
        "label": label,
        "n": len(records),
        "overall_mean": round(sum(r.overall for r in records) / len(records), 3),
        "normalised_mean": round(sum(r.normalised for r in records) / len(records), 4),
        "per_dimension_mean": {
            d: round(sum(v) / len(v), 3) for d, v in sorted(per_dimension.items())
        },
        "task_ids": [r.task_id for r in records],
    }
    data["baselines"].setdefault(baseline_key(key), {})[label] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return entry


def render(log_dir: Path) -> str:
    """`mastery eval` output: per-group trend, plus every skip."""
    records = load_scores(log_dir)
    skips = load_skips(log_dir)
    if not records and not skips:
        return "no quality scores recorded yet"

    # Note the `and not skips`. Returning early on empty `records` alone would
    # report "nothing recorded" for a run whose every stage failed to grade —
    # hiding the holes behind a message that reads like a clean slate. That is the
    # silence this whole module exists to prevent, and it was a real bug here.
    lines: list[str] = []
    if not records:
        lines.append("no quality scores recorded — but see the unscored list below")
        lines.append("")
    for key, group_records in sorted(group(records).items(), key=lambda kv: str(kv[0])):
        lines.append(str(key))
        # Trust state on the same screen as the numbers. A reader who sees a trend
        # without being told the instrument was never checked will assume it was;
        # that assumption is exactly what let a flat 3.0 stand for days.
        verdict, why = calibration.status(key.agent, key.rubric_version)
        if not verdict.trusted:
            lines.append(f"  [{verdict.value.upper()}] {why}")
            lines.append("  these scores cannot carry a baseline until a ladder passes")
        try:
            check_comparable(group_records)
        except IncomparableScores as exc:  # pragma: no cover - grouping prevents it
            lines.append(f"  REFUSED: {exc}")
            continue
        for r in group_records:
            dims = "  ".join(f"{d}={s}" for d, s in sorted(r.dimensions.items()))
            lines.append(
                f"  {r.ts}  {r.task_id}  overall={r.overall}/3 "
                f"({r.normalised:.0%})  {dims}"
            )
        overalls = [r.overall for r in group_records]
        lines.append(
            f"  n={len(overalls)}  mean={sum(overalls) / len(overalls):.3f}/3"
            + (
                f"  first->last {overalls[0]} -> {overalls[-1]}"
                if len(overalls) > 1
                else ""
            )
        )
        lines.append("")

    if skips:
        lines.append(f"unscored ({len(skips)}) — holes in the trend, named:")
        for s in skips:
            lines.append(f"  {s.get('task_id')} ({s.get('agent')}): {s.get('reason')}")

    return "\n".join(lines)
