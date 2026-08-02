"""Output-quality scoring. STOP 7 in BUILD_LEDGER.md.

What this is for: the orchestrator can already prove it behaved correctly — gates
held, schemas validated, caps were charged. None of that says the *output* was any
good. This scores the output, per role, so quality can be trended and so STOP 6's
tiering has something to be measured against.

Four properties are load-bearing, and each one is pinned by a test:

  1. **Write-only.** A score goes to the run log and nowhere else. It never enters
     `orchestrator._corrected()`, never reaches a retry brief, and is never shown
     to the agent that was graded. An agent that can see its own grade optimises
     against the grader, and the number stops measuring the work — so the grade is
     not laundered back into the deliverables under any path.

  2. **Never control flow.** `status` remains the only field the orchestrator
     branches on. A low score does not block acceptance, because making the grader
     a gate would hand control flow to a model. Scores inform the operator, and
     they gate STOP 6, which is a human decision.

  3. **Not self-scored.** A separate invocation with no tools, given the criteria,
     the rubric, and the return. The graded agent's session is over and it has no
     part in producing the number.

  4. **Code does the arithmetic.** The grader returns per-dimension scores and
     nothing else — there is no `overall` field in the schema. The aggregate is
     computed here. Asking a model to total its own scores invites a total that
     does not match its parts, and the mismatch would be invisible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from statistics import mean

from jsonschema import Draft202012Validator

from .brief import ContextItem, TaskBrief
from .config import REPO_ROOT
from .errors import RubricMissing, SchemaViolation
from .schema import Status, TaskResult, extract_json

RUBRICS_PATH = REPO_ROOT / "docs" / "agents" / "quality_rubrics.md"
SCORE_SCHEMA_PATH = REPO_ROOT / "docs" / "agents" / "quality_score_schema.md"

MAX_DIMENSION_SCORE = 3


@lru_cache(maxsize=1)
def _rubrics() -> dict:
    raw = json.loads(RUBRICS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def score_schema() -> dict:
    return json.loads(SCORE_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(score_schema())


def rubric_for(agent: str) -> dict:
    """The agent's rubric, or fail loudly.

    Absence is not permission to skip. A silently unscored output that is still
    accepted as final is precisely the bypass STOP 7's pin exists to catch, so an
    unrubriced agent raises rather than returning None.
    """
    try:
        return _rubrics()[agent]
    except KeyError:
        raise RubricMissing(
            f"no quality rubric for {agent!r} in {RUBRICS_PATH.name}. An accepted "
            f"output cannot be left unscored — add a rubric for this agent, or the "
            f"outcome is unmeasured and cannot be trended."
        ) from None


def has_rubric(agent: str) -> bool:
    return agent in _rubrics()


def require_rubric(agent: str) -> None:
    """Fail closed on a missing rubric, at a point where it costs nothing.

    Called pre-flight by the orchestrator, before a delegation is sent. Same
    reasoning as the gate check: a stop that happens before spend is worth far
    more than the same stop afterwards.
    """
    rubric_for(agent)


def rubric_version(agent: str) -> str:
    return rubric_for(agent)["rubric_version"]


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    score: int
    justification: str


@dataclass(frozen=True)
class QualityScore:
    """A graded output. `overall` is computed here, never taken from the model."""

    task_id: str
    agent: str
    rubric_version: str
    dimensions: tuple[DimensionScore, ...]

    @property
    def overall(self) -> float:
        """Mean of the dimension scores, on the 0-3 scale.

        Unweighted on purpose: a weighting is a judgement about which dimension
        matters more, and inventing one here would bury that judgement in code
        where nobody would find it to argue with.
        """
        return round(mean(d.score for d in self.dimensions), 3)

    @property
    def normalised(self) -> float:
        """`overall` as a 0-1 fraction, for comparing across rubrics with
        different dimension counts."""
        return round(self.overall / MAX_DIMENSION_SCORE, 4)

    def as_log_fields(self) -> dict:
        return {
            "agent": self.agent,
            "rubric_version": self.rubric_version,
            "overall": self.overall,
            "normalised": self.normalised,
            "dimension_scores": [
                {"dimension": d.dimension, "score": d.score, "justification": d.justification}
                for d in self.dimensions
            ],
        }


def build_prompt(brief: TaskBrief, result: TaskResult) -> str:
    """The grading prompt.

    Gets the rubric, the brief's criteria, and the return. Not the context
    payload — the grader is judging the output against a fixed reference, not
    re-doing the task or checking sources for itself.
    """
    return _render(brief, result, rubric_for(brief.agent))


def _render(brief: TaskBrief, result: TaskResult, rubric: dict) -> str:
    """The prompt text, with the rubric passed in rather than looked up.

    Split out for one reason: `prompt_fingerprint` renders this against fixed
    fixtures to get a hash of *what the grader is shown*. Keeping the rubric a
    parameter is what lets that hash stay independent of the rubrics file, so
    the two axes a calibration is bound to — the rubric and the prompt — move
    separately instead of each dragging the other.
    """
    criteria = "\n".join(f"- {c}" for c in brief.success_criteria)
    delivered = "\n".join(f"- {d}" for d in result.deliverables) or "- (none)"
    risks = "\n".join(f"- {r}" for r in result.risks) or "- (none)"

    dims = []
    for d in rubric["dimensions"]:
        anchors = "\n".join(
            f"      {level} — {text}" for level, text in sorted(d["anchors"].items())
        )
        dims.append(f"  {d['dimension']}\n    asks: {d['asks']}\n{anchors}")
    dimensions = "\n\n".join(dims)

    names = [d["dimension"] for d in rubric["dimensions"]]

    return f"""You are grading the quality of one completed task's output against a fixed
rubric. You are not deciding whether the task passed — that decision is already
made and is not yours. You are recording how good the output was, so quality can
be tracked over time.

Grade only what was returned. Do not re-do the work, do not look anything up, and
do not reward or penalise anything the rubric does not ask about.

Use the anchors literally. If the output matches the "1" description, the score is
1, even if it feels harsh. A rubric whose anchors are ignored produces numbers that
drift, and drifting numbers are worse than none.

## The task's own success criteria, for context

{criteria}

## What was returned

status: {result.status.value}
summary: {result.summary}

Deliverables:
{delivered}

Risks named by the agent:
{risks}

next_step: {result.next_step}

## The rubric — agent `{brief.agent}`, version {rubric['rubric_version']}

{dimensions}

## Your reply

One JSON object and nothing else. Score every dimension listed above, exactly
once, using its exact name. Give a one-sentence justification for each, naming
what in the output put it at that level.

Do not compute a total or an average. Report the individual scores only; the
aggregate is computed outside this call.

{{"task_id": "{brief.task_id}", "agent": "{brief.agent}", "rubric_version": "{rubric['rubric_version']}", "dimension_scores": [{", ".join(f'{{"dimension": "{n}", "score": 0-3, "justification": "..."}}' for n in names)}]}}
"""


# -- what the grader is shown, as a hash ------------------------------------
#
# A calibration attests that one rubric discriminates *when a grader is shown a
# particular set of facts about the output*. It was bound to `rubric_version`
# from the start. It was not bound to the prompt, and that was a hole of the
# same shape: change what `_render` puts in front of the grader — add a field,
# drop one, reword the instruction to use the anchors literally — and every
# calibration on file goes on attesting to an instrument that no longer exists,
# with nothing able to notice. Version-binding's own trap, through another door.
#
# So: render the prompt against fixtures that never change and hash the result.
# Sentinels rather than realistic text, one per field, so the hash answers
# exactly one question — which facts reach the grader, in what frame — and moves
# if and only if that answer does.
#
# Deliberately *not* a hash of this module's source: a docstring edit would
# invalidate seventeen ladders and a real change to the fixtures' rendering
# would not be distinguishable from it. Rewording the instructions does move the
# hash, and should: that text is the grader's calibration in the ordinary sense
# of the word.

_CANON_BRIEF = TaskBrief(
    task_id="<task_id>",
    agent="<agent>",
    vertical="<vertical>",
    urgency="<urgency>",
    objective="<objective>",
    success_criteria=("<success_criterion>",),
    context=(ContextItem("<context_label>", "<context_body>"),),
    constraints="<constraints>",
    out_of_scope="<out_of_scope>",
    approval_gates_touched="<approval_gates_touched>",
    expected_deliverables=("<expected_deliverable>",),
)

_CANON_RESULT = TaskResult(
    task_id="<task_id>",
    status=Status.COMPLETE,
    summary="<summary>",
    deliverables=("<deliverable>",),
    risks=("<risk>",),
    next_step="<next_step>",
)

_CANON_RUBRIC = {
    "rubric_version": "<rubric_version>",
    "dimensions": [
        {
            "dimension": "<dimension>",
            "asks": "<asks>",
            "anchors": {"0": "<anchor_0>", "1": "<anchor_1>", "2": "<anchor_2>", "3": "<anchor_3>"},
        }
    ],
}


@lru_cache(maxsize=1)
def prompt_fingerprint() -> str:
    """Short hash of the grading prompt's shape. Calibrations are keyed on it."""
    canon = _render(_CANON_BRIEF, _CANON_RESULT, _CANON_RUBRIC)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


def canonical_prompt() -> str:
    """The fingerprinted text itself, for when a hash mismatch needs diagnosing.

    Printed by `mastery check --prompt`. A fingerprint that has moved says only
    that something changed; this says what, against the last one on record.
    """
    return _render(_CANON_BRIEF, _CANON_RESULT, _CANON_RUBRIC)


def parse(raw: str, *, expected_task_id: str, expected_agent: str) -> QualityScore:
    """Validate a grader return. Same strictness as any other contract.

    Also checks the dimensions against the rubric: a grader that invents a
    dimension, drops one, or scores one twice has not produced a comparable
    number, and a silently partial score would corrupt the trend it feeds.
    """
    try:
        payload = json.loads(extract_json(raw))
    except json.JSONDecodeError as exc:
        raise SchemaViolation(f"quality score is not valid JSON: {exc}", raw=raw) from exc

    errors = sorted(_validator().iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise SchemaViolation(f"quality score failed schema validation: {detail}", raw=raw)

    if payload["task_id"] != expected_task_id:
        raise SchemaViolation(
            f"quality score task_id mismatch: expected {expected_task_id!r}, "
            f"got {payload['task_id']!r}",
            raw=raw,
        )
    if payload["agent"] != expected_agent:
        raise SchemaViolation(
            f"quality score agent mismatch: expected {expected_agent!r}, "
            f"got {payload['agent']!r}",
            raw=raw,
        )

    rubric = rubric_for(expected_agent)
    expected_dims = [d["dimension"] for d in rubric["dimensions"]]
    if payload["rubric_version"] != rubric["rubric_version"]:
        raise SchemaViolation(
            f"quality score claims rubric_version {payload['rubric_version']!r} but "
            f"{expected_agent!r}'s rubric is version {rubric['rubric_version']!r}; "
            f"scores from different versions are not comparable",
            raw=raw,
        )

    got = [d["dimension"] for d in payload["dimension_scores"]]
    if sorted(got) != sorted(expected_dims):
        raise SchemaViolation(
            f"quality score dimensions do not match the rubric: expected "
            f"{sorted(expected_dims)}, got {sorted(got)}",
            raw=raw,
        )

    return QualityScore(
        task_id=payload["task_id"],
        agent=payload["agent"],
        rubric_version=payload["rubric_version"],
        dimensions=tuple(
            DimensionScore(
                dimension=d["dimension"],
                score=d["score"],
                justification=d["justification"],
            )
            # Rubric order, not reply order, so two scores of the same output
            # serialise identically.
            for name in expected_dims
            for d in payload["dimension_scores"]
            if d["dimension"] == name
        ),
    )
