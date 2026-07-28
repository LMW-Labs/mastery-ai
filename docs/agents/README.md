# Agent Roster

Routing index. Read the manager doc first; read one agent doc per delegated task.
System-level rules, pipelines, caps, and contracts live in the root `CLAUDE.md`.

## Tier 1 — always available
| Agent | Owns | Does not own |
|---|---|---|
| [manager](manager.md) | Routing, context delegation, verification, approvals | Execution work |
| [mobile-dev](mobile-dev.md) | App code, builds, release prep (Android/Play) | Design decisions, QA sign-off |
| [researcher](researcher.md) | External evidence discovery | Verifying finished drafts |
| [qa](qa.md) | Regression, edge cases, release readiness | Fixing what it finds |
| [marketing](marketing.md) | Campaign decisions, publishing workflow | Producing its own metrics |
| [risk-review](risk-review.md) | Platform, policy, reputational, safety risk | Legal opinions |
| [strategy](strategy.md) | Prioritization, tradeoffs, sequencing | Execution |
| [ops](ops.md) | VPS, automation, portability, steady state | Live incidents |

## Tier 2 — on demand
| Agent | Owns | Does not own |
|---|---|---|
| [ui-ux](ui-ux.md) | Flows, screens, component specs | Code, release scope |
| [content](content.md) | Copy, hooks, CTAs, scripts | Choosing the angle, verifying claims |
| [fact-checker](fact-checker.md) | Verification pass on drafted output | New evidence discovery |
| [legal-review](legal-review.md) | Legal exposure, counsel escalation | Platform policy, publication clearance |
| [metrics-agent](metrics-agent.md) | KPI definition, measurement, trend detection | Recommending decisions |
| [incident-response-agent](incident-response-agent.md) | Triage, RCA, rollback, postmortem | Steady-state ops |
| [prompt-engineer-agent](prompt-engineer-agent.md) | Agent docs, routing rules, delegation quality | Application code |
| [data-model-agent](data-model-agent.md) | Schemas, output contracts, migrations | Writing or running migrations |

## Tier 3 — periodic
| Agent | Owns | Does not own |
|---|---|---|
| [user-research-agent](user-research-agent.md) | First-party user signal synthesis | Roadmap decisions, competitor data |
| [competitor-intelligence-agent](competitor-intelligence-agent.md) | Named competitors, market moves | Setting positioning |

## Shared contracts
- Task brief in: `task_brief_template.md`
- Structured output: `structured_output_schema.md`
- Manager verdict: `manager_verdict_schema.md` — accept / revise / reject
- Routing logic: `manager_decision_rubric.md` — rewritten for the full 18-agent roster

## Enforcement note
Nothing in these files is self-enforcing. Caps, retries, timeouts, tool allowlists, pipeline
sequencing, and output validation are the orchestrator's job. Each `Rules and guardrails`
section is a spec for code that must already exist — that code is `mastery/`, and
`docs/orchestrator.md` maps each guardrail to the module that enforces it.

Agent docs are **not** auto-loaded for delegated sub-agents. The manager must pass the
relevant doc in the `context` payload or the sub-agent has no role definition.
