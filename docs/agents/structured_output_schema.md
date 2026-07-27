# structured_output_schema

The return contract for every delegated sub-agent task. Enforced by the orchestrator, not by
the model. A return that fails validation is a **task failure** — it is not repaired, patched,
or re-prompted into shape. See `CLAUDE.md` → Task and output contracts.

Applies to sub-agent → manager returns only. The manager's reply to the operator is prose and
is not validated against this schema.

## Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "mastery-ai/agent-output",
  "title": "Agent Output",
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "summary", "deliverables", "risks", "next_step"],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^[0-9]{8}-(ff|rd|ops)-[0-9]{3}$",
      "description": "Echoes the brief's task_id exactly. Mismatch is a validation failure."
    },
    "summary": {
      "type": "string",
      "pattern": "^(COMPLETE|PARTIAL|FAILED): ",
      "minLength": 12,
      "maxLength": 600,
      "description": "Outcome verdict, then what was done, in the agent's own words."
    },
    "deliverables": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["label", "content"],
        "properties": {
          "label": { "type": "string", "minLength": 1, "maxLength": 120 },
          "content": { "type": "string", "minLength": 1 }
        }
      },
      "description": "Shape of the contents is set by the agent's own doc."
    },
    "risks": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["severity", "detail"],
        "properties": {
          "severity": { "enum": ["low", "medium", "high", "blocker"] },
          "detail": { "type": "string", "minLength": 1 }
        }
      },
      "description": "Present always. Empty array means risk was considered and none found."
    },
    "next_step": {
      "type": "string",
      "minLength": 1,
      "maxLength": 400,
      "description": "The single next action, and who owns it."
    }
  }
}
```

## Outcome verdicts

`summary` opens with one of three, followed by `: `.

| Verdict | Means |
|---|---|
| `COMPLETE` | Every success criterion in the brief was met. |
| `PARTIAL` | Some criteria met. The unmet ones are named in `summary`. |
| `FAILED` | The task could not be done as briefed. |

A `FAILED` return still carries at least one deliverable: one labeled `failure`, stating what
was attempted, where it stopped, and what would unblock it. Failing honestly is a valid
completion of the contract. Returning `COMPLETE` over partial work is not.

## Escalation

There is no separate escalation field. An agent escalating per its own doc returns:

- a `risks` entry at severity `blocker`, naming the escalation trigger, and
- a `next_step` naming the operator or the receiving agent.

The orchestrator halts the run on any `blocker` and returns to the operator.

## Validation rules

- `additionalProperties: false` at every level. Extra keys fail.
- `task_id` must match the brief. A drifted or invented ID fails.
- `deliverables` cannot be empty. "Nothing to report" is a `FAILED` return with a failure deliverable.
- `risks` must be present. Omission fails; `[]` is the way to say none.
- Validation failure is reported to the operator as a task failure. It is not retried silently,
  and the schema is never loosened to accommodate an agent that keeps failing it.

## Example

```json
{
  "task_id": "20260727-ff-014",
  "summary": "PARTIAL: Fixed the crash on empty feed refresh. Could not reproduce the reported duplicate-post defect from the steps given.",
  "deliverables": [
    {
      "label": "FeedViewModel.kt",
      "content": "Guarded the empty-list branch before index access. Full file contents follow: ..."
    },
    {
      "label": "manual test steps",
      "content": "1. Cold start with no cached posts. 2. Pull to refresh. 3. Expect empty state, not crash."
    }
  ],
  "risks": [
    {
      "severity": "medium",
      "detail": "Duplicate-post defect remains open and unreproduced. The brief's steps did not trigger it on this build."
    }
  ],
  "next_step": "qa runs the manual test steps above; duplicate-post defect needs a new reproduction from the reporter."
}
```
