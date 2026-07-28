# CLAUDE.md

## Project overview

Personal agent operating system for Austin. Code-owned, guardrail-driven, multi-agent.
The manager orchestrates all work and delegates narrow tasks to specialized sub-agents.
Sub-agents receive only the context the manager explicitly passes.

This file is intentionally high-level. Per-agent detail lives in `docs/agents/`.
Read the one agent doc relevant to the task. Do not read the whole directory.

## Core principles

- Guardrails are enforced in orchestrator code, not in this file.
- The manager is the only agent with full mission context.
- Sub-agents operate on scoped, delegated context only.
- Prefer honest failure over fabricated success.
- No uncapped loops, uncapped input, or silent failover.
- Keep workflows small, observable, and debuggable.
- Keep agent responsibilities narrow and composable.
- Progressive disclosure: new detail goes in a separate file, not in this one.

## Primary verticals

### FaithFeed
Mobile app iteration on **Android / Google Play (live)**. Features, bug fixes, UI/UX,
QA and regression, KPI monitoring, campaign support via integrations.
**iOS / Apple App Store is future scope, not started.**

### Research and Debunk
Research claims, source evidence, identify false or misleading claims, draft posts and
responses, improve hooks and CTAs, review public-facing language for risk.

### Operations and Sourcing
Project discovery and prioritization, VPS and mobile portability, remote shell workflows,
strategy and execution planning.

## Agent roster and routing

Read the linked doc before delegating. Full index: `docs/agents/README.md`.

### Tier 1 — always available
| Agent | Owns | Does not own |
|---|---|---|
| [manager](docs/agents/manager.md) | Routing, context delegation, verification, approvals | Execution work |
| [mobile-dev](docs/agents/mobile-dev.md) | App code, builds, release prep | Design decisions, QA sign-off |
| [researcher](docs/agents/researcher.md) | External evidence discovery | Verifying finished drafts |
| [qa](docs/agents/qa.md) | Regression, edge cases, release readiness | Fixing what it finds |
| [marketing](docs/agents/marketing.md) | Campaign decisions, publishing workflow | Producing its own metrics |
| [risk-review](docs/agents/risk-review.md) | Platform, policy, reputational, safety risk | Legal opinions |
| [strategy](docs/agents/strategy.md) | Prioritization, tradeoffs, sequencing | Execution |
| [ops](docs/agents/ops.md) | VPS, automation, portability, steady state | Live incidents |

### Tier 2 — on demand
| Agent | Owns | Does not own |
|---|---|---|
| [ui-ux](docs/agents/ui-ux.md) | Flows, screens, component specs | Code, release scope |
| [content](docs/agents/content.md) | Copy, hooks, CTAs, scripts | Choosing the angle, verifying claims |
| [fact-checker](docs/agents/fact-checker.md) | Verification pass on drafted output | New evidence discovery |
| [legal-review](docs/agents/legal-review.md) | Legal exposure, counsel escalation | Platform policy, publication clearance |
| [metrics-agent](docs/agents/metrics-agent.md) | KPI definition, measurement, trend detection | Recommending decisions |
| [incident-response-agent](docs/agents/incident-response-agent.md) | Triage, RCA, rollback, postmortem | Steady-state ops |
| [prompt-engineer-agent](docs/agents/prompt-engineer-agent.md) | Agent docs, routing rules, delegation quality | Application code |
| [data-model-agent](docs/agents/data-model-agent.md) | Schemas, output contracts, migrations | Writing or running migrations |

### Tier 3 — periodic
| Agent | Owns | Does not own |
|---|---|---|
| [user-research-agent](docs/agents/user-research-agent.md) | First-party user signal synthesis | Roadmap decisions, competitor data |
| [competitor-intelligence-agent](docs/agents/competitor-intelligence-agent.md) | Named competitors, market moves | Setting positioning |

## Mandatory pipelines

These sequences are enforced in orchestrator code. The manager cannot skip a stage.

**Any public-facing output:**
`content` → `fact-checker` → `risk-review` → operator approval → publish

- A `not publishable` from fact-checker or a `hold` from risk-review halts the pipeline.
- `legal-review` is inserted when either reviewer escalates, or when a real party is named.

**Any release:**
`mobile-dev` → `qa` → operator approval → promote to track

- A qa `no-go` halts the pipeline. Deadline pressure does not override it.

## Approval gates

When an approval gate is hit, the orchestrator halts the run and returns to the operator.
It does not proceed, queue, or assume approval. Gate triggers:

- Money: spend, billing, plan tier, new payment method.
- Production: deploys, track promotion, publishing, live config.
- Permissions: new access, wider network exposure, loosened auth.
- Public output: anything posted, listed, or shipped to users.
- Destructive or irreversible operations.
- Any use of a paid tool or metered API not already authorized.

## Orchestrator requirements

These are code requirements, not instructions to a model. A model cannot enforce them.
The enforced values live in `mastery/config.py`; the table below is the current setting
and where it is applied.

| Requirement | Value | Enforced in |
|---|---|---|
| Max delegations per operator request | 5 | `orchestrator._charge_delegation` |
| Max turns, manager | 12 (unused; manager is code, verification takes 1 turn) | — |
| Max turns, sub-agent | 6 | `delegate.run_task` → `max_turns` |
| Max context bytes per delegation | 60,000; over-limit briefs rejected, never truncated | `brief.validate` |
| Retries per failed task | 1, then fail honestly | `orchestrator.execute` |
| Spawn depth | 1 — the `Agent` tool is denied to sub-agents | `delegate.SdkRunner` |
| Task timeout | 300s | `delegate.run_task` |
| Output validation | reject on schema failure; no repair path exists | `schema.parse` |

Context isolation is enforced by `setting_sources=[]` on every delegation: the SDK does
not auto-load this file, project settings, or user settings into a sub-agent. The only
context a sub-agent sees is the brief's payload.

Additional: no silent retry escalation, no silent model upgrade, no silent billable
fallback, no fabricated completion, no filling missing context with assumptions.

## Task and output contracts

**Task ID:** `YYYYMMDD-<vertical>-<nnn>` — verticals `ff` (FaithFeed), `rd` (Research and
Debunk), `ops`. Example: `20260727-ff-014`.

**Delegated task in:** `task_brief_template.md`, fully filled. No blank sections.

**Delegated task out:** strict JSON per `structured_output_schema.md`.
`additionalProperties: false`. All of `task_id`, `status`, `summary`, `deliverables`,
`risks`, `next_step` required. Validation failure is a task failure, not something to patch.

`status` is the only field the orchestrator branches on. It is never inferred from prose.

| status | Meaning | Orchestrator action |
|---|---|---|
| `complete` | Success criteria met in full | Accept, continue pipeline |
| `partial` | Some criteria met, gaps named in `risks` | Return to manager for accept-or-retry |
| `failed` | Could not complete; reason in `summary` | One retry with corrected brief, then report |
| `blocked` | Hit an approval gate or missing prerequisite, OR is a gate returning closed (risk-review hold, fact-checker not-publishable, qa no-go, legal-review counsel-required) | **Halt. Return to operator.** No retry |

`summary`, `risks`, and `next_step` are prose for humans. Never parse them for control flow.
A `blocked` return names the gate in `next_step`.

Any escalation case returns `blocked`, naming the trigger in `next_step`.
A stop condition outside the escalation list returns `failed`.

**Manager verdict:** accept / revise / reject is control flow and is schema-bound, per
`structured_output_schema.md`'s sibling `manager_verdict_schema.md`. It is produced by a
**verify-only** manager invocation — one turn, no tools, given the brief's success
criteria and the return, and nothing else. `complete` is never auto-accepted; every
`complete` and `partial` return is verified before the pipeline continues.

| verdict | Meaning | Orchestrator action |
|---|---|---|
| `accept` | Every success criterion is met by what was returned | Continue pipeline |
| `revise` | A nameable gap a corrected brief could close; `revision_note` required | Retry, within the retry cap |
| `reject` | Wrong work, or a gap retrying cannot close | Report to operator |

A `revise` consumes the same retry budget as a `failed` return. Two attempts, then report.

**Manager to operator (chat):** prose or bullets. Short answer, what failed, what needs
approval, recommended next step. The strict schema does not apply here.

## Context delegation

- Context is opt-in and assembled by hand per task.
- Never pass this file, full chat history, or unrelated project docs to a sub-agent.
- Pass the sub-agent's own doc from `docs/agents/` in the context payload — agent docs are
  **not** auto-loaded for delegated sub-agents.
- Include prior accepted outputs only when the new task depends on them.

`mastery draft` proposes briefs from a raw request; it never runs them. It writes each
stage's `context` as `<<< FILL >>>` placeholders and stops. Filling them is the operator's
step, and it is the step that keeps this section true — a drafter that assembled context
itself would move context selection into a model.

## Project-specific notes

- FaithFeed is live on Google Play. Apple is planned, not started.
- The system must stay usable from a VPS and a mobile shell.
- There is no per-role model routing; `delegation.model` is global.
- **Auth runs on the Claude Code OAuth credential** (`~/.claude/.credentials.json`),
  verified working with claude-agent-sdk 0.2.128. `auth.mode="subscription"` asserts no
  `ANTHROPIC_API_KEY` is present, because a set key would silently shadow OAuth and bill
  the API account instead — the "silent billable fallback" this file forbids. Usage draws
  down the same budget as interactive Claude Code, so it is quota, not dollars.
  `auth.mode="api_key"` remains available and crosses the money gate deliberately.
- Orchestrator code location: `mastery/`. Entry point `mastery.cli`:
  - `mastery check` — validates config, roster, and schemas without a model call.
  - `mastery draft <request>` — proposes briefs. Does not run them.
  - `mastery run <brief.json>` — runs one brief to a verified outcome.

  The delegation cap is per operator request, and one `mastery run` is one request. A plan
  whose stage count reaches the cap is run as separate `mastery run` invocations, not as a
  single pipeline — otherwise the first retry raises `CapExceeded` with earlier stages
  already spent.
