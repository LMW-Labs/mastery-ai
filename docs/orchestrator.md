# orchestrator

The code that owns the guardrails. `docs/agents/` describes intent; this describes what is
actually enforced, and where.

## Layout

| Module | Owns |
|---|---|
| `config.py` | The caps, as enforced values. One place to change a limit. |
| `ids.py` | Task IDs — same pattern as the output schema, so a bad echo fails validation. |
| `roster.py` | The 19 agents as routing data. `tests/test_contracts.py` asserts it matches `docs/agents/`. |
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
| Never pass CLAUDE.md or history to a sub-agent | `setting_sources=[]` plus a prompt built only from the brief's payload — **verified**, probe 5 |
| Spawn depth 1 | The `Agent` tool is in `delegation.denied_tools` — **verified**, probe 6 |
| Delegations are read-only | `permission_mode="dontAsk"` — **verified**, probe 7. Not `allowed_tools`; see below |
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

## `allowed_tools` does not restrict anything

The SDK advertises its full tool set — 25 tools — to every delegation, whatever
`allowed_tools` says. That field only *pre-approves*: listed tools run without
prompting, unlisted ones fall through to `permission_mode`. So `WebSearch`,
`WebFetch`, `SendMessage`, `PushNotification`, and the scheduling tools are all
visible to a sub-agent, and what actually stops them is `permission_mode="dontAsk"`.

This matters because the failure is silent. Setting `permission_mode` to
`acceptEdits` or `bypassPermissions` gives every delegation network egress and
write access while `allowed_tools=["Read","Glob","Grep"]` still reads as
read-only. Probe 7 asserts the denial directly — run it after touching that field.

`ResultMessage.permission_denials` carries the same signal in production: it lands
in the run log on every delegation, so a sub-agent reaching outside its allowlist
is visible without going looking for it.

## Gates have two layers, and only one of them is a model

The primary control is `gates.enforce`, reading the brief's declared
`Approval gates touched` field before anything is sent. That is deterministic code:
it halts every time, and it cannot be talked out of it.

The backstop is the sub-agent noticing a gate the brief failed to declare, and returning
`blocked`. That is a model, so it is probabilistic.

`scripts/measure_blocked.py` tests the backstop specifically — every case declares
`none`, so the primary control passes it through on purpose. All eight halted anyway.

The ordering is what makes this tolerable: a brief that honestly declares its gate never
reaches a model at all, and the probabilistic layer only ever runs on briefs that were
mis-declared in the first place. Do not invert this by relying on sub-agents to catch
gates the brief should have named.

## Verifying

Two suites, and they cover different things:

```
python -m unittest discover -s tests -t .   # 70 tests, offline, no credential
python scripts/probe.py                     # 3 guardrails, real calls, ~$0.5 quota
python scripts/measure_schema.py 20         # happy-path contract, ~$3 quota
python scripts/measure_blocked.py           # 8 halt triggers, ~$1.2 quota
```

The unit suite proves the orchestrator is internally consistent against a fake
runner. It **cannot** prove the guardrails, because the guardrails are SDK
behaviour — a fake runner will happily agree that `setting_sources=[]` works.
`scripts/probe.py` is what makes them real, and each probe isolates one claim so
a failure localizes itself. Probe 5 uses a control run (`setting_sources=["project"]`)
so its negative result is evidence rather than a model simply saying "I don't know".

Run the probes after an SDK upgrade or any change to `delegation` in `config.py`.

## Running it

```
python -m mastery.cli check            # config, roster, schemas — no model call
python -m mastery.cli run brief.json   # one delegation
python -m unittest discover -s tests -t .
```

The test suite runs without the SDK, a network, or a credential — every guardrail is
provable against a scripted fake runner (`tests/test_orchestrator.py`).

## Open

- **Schema compliance is measured on the happy path only.** `scripts/measure_schema.py`
  ran 20 real delegations across five agent docs on `sonnet`: 20/20 schema-valid. Rule of
  three puts the 95% upper bound on the per-call failure rate at ~15%, and a retry budget
  of 1 exhausts only on two consecutive failures — ~2.2% at that bound. Defensible.

  p² assumes independent failures; a retry meets the same prompt and model, so correlated
  failure makes the real two-consecutive rate higher than p². Re-run after changing
  `delegation.model`.

- **The blocked path is covered, at n=1 per trigger.** `scripts/measure_blocked.py` runs
  all eight ways a delegation can legitimately halt — missing context, the four approval
  gates, and the three review gates returning closed. 8/8 schema-valid, 8/8 correctly
  `blocked`. Across both scripts that is 28/28 schema-valid overall (~11% upper bound).

  Read it as *the behaviour works and is typical*, not as a rate: one sample per trigger
  cannot distinguish 99% from 80%. It matters less than it looks, because the model is the
  **second** layer here — see below.
- **`max_context_bytes` is a guess at 60,000.** It has never been checked against a real
  brief. Revisit once a few have actually been sent.
- **Quota, not dollars.** On subscription auth a trivial call reported ~$0.125 notional.
  A five-delegation pipeline carrying real agent docs is not cheap in quota, and nothing
  currently handles hitting a limit mid-pipeline.
- **`max_turns` for the manager is unused.** The manager is code; its one model call is
  verify-only and takes a single turn. The cap stays in config in case a conversational
  manager loop is ever added.
- **No routing implementation.** `manager_decision_rubric.md` is applied by the operator
  when writing a brief; `roster.py` validates the choice but does not make it.
