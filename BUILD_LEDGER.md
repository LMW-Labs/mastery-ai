# BUILD LEDGER — Mastery OS

North star: the governor layer (safe, cheap, auditable orchestration) is the product; agents are the commodity. Every stop below moves toward auditability, cost control, or compounding state.

## Operating rules for the driver
- Do ONE stop at a time, in order. Do not start the next stop until the current one's DONE-WHEN is fully met.
- Check the box only when DONE-WHEN is verified, not when code is written.
- Stop and ask for approval at any money / prod / permissions / public-output decision.
- This ledger is the Mastery OS build track ONLY. The FDE/GitHub portfolio track is separate and must not be interleaved.
- If a stop reveals new work, log it under BACKLOG — do not expand the current stop.

---

## STOP 1 — Schema: telemetry + status
- [ ] Add required `status` enum: `success | partial | failed | blocked`
- [ ] Add `tokens` (int), `model_tier` (string), `tool_tier` (string) fields
- [ ] Keep `additionalProperties: false`
- DONE-WHEN: a failed task produces structurally different output than a success; schema still validates closed; every field populated on a dry run.
- NEXT → Stop 2

## STOP 2 — Rubric: risk overlay + coverage + naming
- [ ] Move approval/risk (money/prod/permissions/public) to a non-short-circuiting overlay evaluated BEFORE routing
- [ ] Verify "deploy feature to prod" routes to approval, not Developer
- [ ] Reconcile emitted names (`Developer`/`Designer`) with roster (`mobile-dev`/`ui-ux`)
- [ ] Decide wire-or-cut for the 13 unreachable agents; remove or route each
- DONE-WHEN: no defined-but-unreachable agent exists; every emitted route name matches a roster entry; the prod-deploy test hits approval.
- NEXT → Stop 3

## STOP 3 — Routing as pure code
- [ ] Make route selection a deterministic code function (first-match-stop), zero LLM calls
- [ ] `roster.py` validates the selected name
- DONE-WHEN: routing spends 0 tokens; roster validation passes on all live routes.
- NEXT → Stop 4

## STOP 4 — Persistent state layer (Supabase)
- [ ] Persist research/debunk verdicts keyed by claim hash
- [ ] Persist KPI history
- [ ] Persist reject-with-reason as structured rows
- DONE-WHEN: a repeat claim reuses a stored verdict instead of recomputing; a rejection writes a queryable row.
- NEXT → Stop 5

## STOP 5 — Manager context from state, not inline
- [ ] Manager reads sub-briefs/returns selectively from a state file/scratchpad
- [ ] Stop carrying all returns inline across stages
- DONE-WHEN: manager window does not grow linearly with stage count on a multi-stage run.
- NEXT → Stop 6

## STOP 6 — Prompt cache + model tiering
- [ ] Prompt-cache static prefix (system prompts, agent `.md`, rubric, schema)
- [ ] Cheap model for routing/validation/verify/fact-check; expensive only for synthesis
- DONE-WHEN: telemetry (Stop 1) shows correct tier per call; static prefix not re-billed per call.
- NEXT → Stop 7

## STOP 7 — Output-quality eval loop
- [ ] Score output quality per run (not just orchestration mechanics)
- [ ] Log scores so they trend run-over-run
- DONE-WHEN: each run emits a quality score; scores are queryable over time.
- NEXT → Decision Gate

## DECISION GATE — before first live run
- [ ] RESOLVE: agent runtime shares subscription limits vs. separate metered API key
- DONE-WHEN: auth mode chosen and hardwired; no ambiguity at runtime.
- NEXT → Stop 8

## STOP 8 — First live run (staged)
- [ ] Researcher only, stateless mode, hand-carry output between stages
- [ ] Capture telemetry; observe each boundary
- DONE-WHEN: one full stage runs live with telemetry recorded and no guardrail bypassed.
- NEXT → iterate; system is now minimally complete on the governor track.

---

## BACKLOG (log, do not action mid-stop)
- Cap CONTEXT/history in brief with rolling summary
- Bound `deliverables[]` item length
- Fix filename typo `task_breif_template.md` (only if a path references it)
