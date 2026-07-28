# orchestrator

The code that owns the guardrails. `docs/agents/` describes intent; this describes what is
actually enforced, and where.

## Layout

| Module | Owns |
|---|---|
| `config.py` | The caps, as enforced values. One place to change a limit. |
| `ids.py` | Task IDs — same pattern as the output schema, so a bad echo fails validation. |
| `roster.py` | The 18 agents as routing data. `tests/test_contracts.py` asserts it matches `docs/agents/`. |
| `brief.py` | The delegation contract. Rejects unfilled and over-limit briefs. |
| `gates.py` | Approval gates. Checked before work is briefed. |
| `schema.py` | Parse, validate, and branch on `status`. No repair path. |
| `verdict.py` | Manager verify-only invocation and its verdict contract. |
| `pipelines.py` | The two mandatory sequences. `advance()` is the only way forward. |
| `delegate.py` | The only module that imports `claude-agent-sdk`. |
| `orchestrator.py` | The run loop. |
| `runlog.py` | One JSONL per operator request. |
| `cli.py` | `mastery check`, `mastery run <brief.json>`. |

## Where each guardrail lives

| CLAUDE.md rule | Enforced by |
|---|---|
| Gate halts before work is briefed | `orchestrator.execute` calls `gates.enforce` before the first delegation |
| No proceeding, queuing, or assuming approval | `gates` has no `approve()`; approval arrives as a new operator request |
| `status` is the only branch; never inferred from prose | `schema.ACTION_FOR` maps the enum; `summary` is never parsed |
| Validation failure is a task failure | `schema.parse` raises; `orchestrator` counts it as an attempt |
| Never pass CLAUDE.md or history to a sub-agent | `setting_sources=[]` plus a prompt built only from the brief's payload |
| Spawn depth 1 | The `Agent` tool is in `delegation.denied_tools` |
| Context is opt-in, assembled by hand | `brief.build` takes an explicit item list; oversize is rejected, not truncated |
| Two attempts, then report | `caps.retries_per_failed_task`, counted across both failed returns and `revise` verdicts |
| Pipelines cannot be skipped or reordered | `pipelines.Pipeline.advance` is the only traversal; the stage callback cannot choose a stage |
| No fabricated completion | `complete` still goes through manager verification |

## Delegation is a flat `query()`, not an SDK subagent

The SDK can host subagents itself (`ClaudeAgentOptions.agents`). This orchestrator does not
use that for delegation, because it would move two decisions into a model that CLAUDE.md
puts in code: which agent handles a task, and what context that agent sees. Instead each
delegation is its own `query()` with a hand-built prompt, a locked-down tool set, and no
filesystem-loaded settings.

## Running it

```
python -m mastery.cli check            # config, roster, schemas — no model call
python -m mastery.cli run brief.json   # one delegation
python -m unittest discover -s tests -t .
```

The test suite runs without the SDK, a network, or a credential — every guardrail is
provable against a scripted fake runner (`tests/test_orchestrator.py`).

## Open

- **Auth is unconfirmed** — see the note in CLAUDE.md. `auth.mode` defaults to `inherit`.
- **`max_context_bytes` is a guess at 60,000.** It has never been checked against a real
  brief. Revisit once a few have actually been sent.
- **`max_turns` for the manager is unused.** The manager is code; its one model call is
  verify-only and takes a single turn. The cap stays in config in case a conversational
  manager loop is ever added.
- **No routing implementation.** `manager_decision_rubric.md` is applied by the operator
  when writing a brief; `roster.py` validates the choice but does not make it.
