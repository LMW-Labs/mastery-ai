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
Confirm and set the actual values in config; the numbers below are the starting proposal.

| Requirement | Value |
|---|---|
| Max delegations per operator request | 5 |
| Max turns, manager | 12 |
| Max turns, sub-agent | 6 |
| Max context bytes per delegation | set explicitly; reject over-limit briefs |
| Retries per failed task | 1, then fail honestly |
| Spawn depth | 1 (flat; sub-agents do not delegate) |
| Task timeout | 300s |
| Output validation | reject on schema failure; do not repair silently |

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

> **Open:** manager accept/revise/reject verdicts are control flow but are not
> schema-bound. Resolve during orchestrator design — either a minimal manager
> verdict schema or a verify-only invocation. Do not auto-accept on `status`
> alone; manager verification still applies to `complete` returns.

**Manager to operator (chat):** prose or bullets. Short answer, what failed, what needs
approval, recommended next step. The strict schema does not apply here.

## Context delegation

- Context is opt-in and assembled by hand per task.
- Never pass this file, full chat history, or unrelated project docs to a sub-agent.
- Pass the sub-agent's own doc from `docs/agents/` in the context payload — agent docs are
  **not** auto-loaded for delegated sub-agents.
- Include prior accepted outputs only when the new task depends on them.

## Project-specific notes

- FaithFeed is live on Google Play. Apple is planned, not started.
- The system must stay usable from a VPS and a mobile shell.
- Claude Code CLI and the agent runtime share the same subscription auth — usage limits are
  a shared budget. There is no per-role model routing; `delegation.model` is global.
- Orchestrator code location: `<fill in>`.
