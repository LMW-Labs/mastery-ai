# manager_decision_rubric

Routing logic for the manager. Applied in order — the first rule that fires decides.
Covers the full 18-agent roster in `README.md`.

Selection produces **exactly one** agent per brief. A request needing two agents is split
into two sequential briefs, each routed through this rubric on its own.

---

## Step 0 — Is the request scoped?

If the objective cannot be written as one checkable sentence, do not route it.
Return to the operator for scope, or split it into tasks that can be.

Not scoped: "make FaithFeed better", "look into the retention thing".
Scoped: "fix the crash on empty-feed refresh", "pull 30-day D7 retention vs prior period".

## Step 1 — Does it touch an approval gate?

If the request itself changes money, production, permissions, or public output, or is
destructive or irreversible — **halt and return to the operator before delegating.**
The gate is checked before the work is briefed, not after it comes back.

Preparing a gated action is delegable. Executing one is not.

## Step 2 — Is a mandatory pipeline triggered?

Pipelines are enforced in orchestrator code. The manager cannot skip a stage or reorder one.

**Public-facing output:** `content` → `fact-checker` → `risk-review` → operator approval → publish
- `legal-review` is inserted when either reviewer escalates, or when a real party is named.
- `not publishable` from fact-checker, or `hold` from risk-review, halts the pipeline.

**Release:** `mobile-dev` → `qa` → operator approval → promote to track
- A qa `no-go` halts the pipeline. Deadline pressure does not override it.

If a pipeline is triggered, the pipeline sets the sequence. Route the first stage only;
each subsequent stage is briefed after the prior one returns and is accepted.

## Step 3 — Route by trigger

First match wins, read top to bottom.

| If the task is… | Route to |
|---|---|
| Something is down, degraded, or actively failing | incident-response-agent |
| App code, build config, versioning, or Play Console artifact | mobile-dev |
| Verifying a change, regression, or release readiness | qa |
| Screen, flow, component spec, or usability design | ui-ux |
| Finding external evidence for an open question or claim | researcher |
| Writing copy, hooks, CTAs, scripts, or variants | content |
| Adjudicating claims in an already-drafted piece | fact-checker |
| Policy, reputational, safety, or privacy screen on output | risk-review |
| Defamation, IP, regulated claims, contracts, minors' data | legal-review |
| Campaign structure, scheduling, kill/scale/hold decisions | marketing |
| Producing figures, KPI definitions, trend or regression detection | metrics-agent |
| Prioritization, option comparison, sequencing, tradeoffs | strategy |
| VPS, automation, backups, secrets, portability — system healthy | ops |
| Schema, output contract, entity relationships, migration design | data-model-agent |
| Synthesizing first-party user feedback into themes | user-research-agent |
| Tracking named competitors' shipped changes or positioning | competitor-intelligence-agent |
| Fixing the agent system's own docs, briefs, or routing | prompt-engineer-agent |

## Step 4 — Apply tie-breakers

Where two agents look plausible, the distinction is already written in the "Does not own"
column of `README.md`. The recurring confusions:

| Confusion | Rule |
|---|---|
| researcher vs fact-checker | Open question, nothing drafted yet → researcher. A draft exists and its claims need adjudicating → fact-checker. |
| ops vs incident-response-agent | System healthy → ops. Down or degraded → incident-response-agent, immediately. |
| risk-review vs legal-review | Platform policy, reputation, safety → risk-review. Legal exposure specifically → legal-review, and only when gated in. |
| metrics-agent vs marketing | Producing the number → metrics-agent. Deciding what to do about it → marketing. |
| strategy vs manager | Comparing options and recommending → strategy. Choosing who executes → manager. |
| content vs marketing | Writing the words → content. Choosing the angle, channel, and timing → marketing. |
| mobile-dev vs qa | Making the change → mobile-dev. Verifying it → qa. Never the same brief. |
| mobile-dev vs data-model-agent | Implementing against a schema → mobile-dev. Designing or changing the schema → data-model-agent first. |
| ui-ux vs mobile-dev | Deciding what it should look like or do → ui-ux. Building it → mobile-dev, against that spec. |
| user-research vs competitor-intelligence | Our users → user-research-agent. Their product → competitor-intelligence-agent. |
| prompt-engineer-agent vs manager | Recurring routing failure → prompt-engineer-agent. One-off misroute → manager corrects and moves on. |

## Step 5 — No agent fits

Do not route to the closest available agent. Do not widen an agent's scope to absorb the task.
Return to the operator: state what the task needs and that no agent in the roster owns it.

A missing, redundant, or wrongly-split agent is a roster problem — hand it to
`prompt-engineer-agent` once it recurs, not on the first occurrence.

---

## Routing failures to avoid

- Routing a two-domain request to one agent because it is "mostly" theirs.
- Skipping `fact-checker` because content sourced its own claims.
- Skipping `qa` because the change was small.
- Sending `researcher` a finished draft to check.
- Letting `metrics-agent` recommend, or `marketing` compute.
- Delegating a gated action instead of halting at the gate.
- Re-delegating a failed task a third time. Two attempts, then report the failure.
