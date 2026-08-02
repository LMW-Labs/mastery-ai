# BUILD LEDGER — Mastery OS

North star: the governor layer (safe, cheap, auditable orchestration) is the product; agents are the commodity. Every stop below moves toward auditability, cost control, or compounding state.

## Operating rules for the driver
- Do ONE stop at a time, in order. Do not start the next stop until the current one's DONE-WHEN is fully met.
- Check the box only when DONE-WHEN is verified, not when code is written.
- Stop and ask for approval at any money / prod / permissions / public-output decision.
- This ledger is the Mastery OS build track ONLY. The FDE/GitHub portfolio track is separate and must not be interleaved.
- If a stop reveals new work, log it under BACKLOG — do not expand the current stop.
- A stop marked MET carries its evidence inline. A claim without a file, line, or log path is not evidence.

Revised 2026-07-29 after auditing the stop list against the code. Four stops were already
satisfied, one described a different codebase, and one contradicted CLAUDE.md. Those are
recorded below as MET or CUT **with their evidence and reasons**, not deleted — a ledger
that quietly drops its own errors cannot be audited either.

---

## STOP 1 — Enforce status + orchestrator-side telemetry — MET
- [x] Status enum: KEEP existing `complete` member — do NOT rename. Satisfied iff the enum also carries a distinct honest-failure state (failed/blocked/partial) AND `status` is required. If the enum is `complete`-only, THAT is the real work here.
      - MET on inspection, no code change: `schema.py:33-39` defines all four members, and `structured_output_schema.md:4,10-13` has `status` in `required` with the four-value enum. Not `complete`-only.
- [x] Record `model_tier` + `tool_tier` in `runlog.py` (orchestrator's own dispatch decision — no fabrication risk). Reuse existing `cost_usd` / `num_turns`; do not duplicate. Join to task output by `task_id`.
- [x] Also capture token counts and the cache split — `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens` — from `ResultMessage.model_usage`. Not a duplicate of `cost_usd`: Stop 6's DONE-WHEN needs the cache-read vs cache-creation split, and a dollar figure cannot supply it. Verified present in claude-agent-sdk 0.2.128.
- [x] Do NOT add `tokens`/`model_tier`/`tool_tier` to the task-output schema. A sub-agent cannot know SDK metadata; self-reported numbers = fabrication.
- [x] Keep task-output schema `additionalProperties: false`.
- DONE-WHEN: run log emits per-task cost + tier joined by `task_id`; honest failure is structurally distinguishable in output; no telemetry field is model-produced.

**Verified 2026-07-29.** Suite 98 → **109 passed, 15 subtests**; `mastery check` exit 0.

- WHAT CHANGED: `delegate.Usage` + `usage_from()` fold `ResultMessage.model_usage`
  (camelCase, keyed by model) into typed counts; `SdkRunner.run` reads it at the one place
  that sees a `ResultMessage`; it rides `RunnerResult` → `Invocation` → the log.
  `runlog.delegation_start` records `tool_tier` from `roster.py`; `delegation_end` and
  `verdict` both record tokens, the cache split, and `model_tier`.
- COST JOIN: a stage's true cost is `delegation_end` **plus every `verdict` on that
  `task_id`** — the verdict is a real model call, and omitting it under-reported every run
  by one call per stage. Dry run: delegation $0.0912 + verdict $0.0071 = **$0.0983**, where
  the old log would have shown $0.0912.
- CACHE SPLIT: kept as two fields, never summed into a total. `total_tokens` is fresh
  input + output only; folding cache reads in would hide the one thing the split exists to
  show. This is what Stop 6 measures against.
- MODEL: records the *resolved* model (`canonicalModel`, e.g. `claude-sonnet-4-5`), not the
  requested alias — `config.delegation.model` is `"sonnet"`, which is neither what gets
  billed nor what a tiering decision can be checked against.
- NO FABRICATION: asserted, not asserted-in-prose. `test_no_telemetry_field_exists_in_the_task_output_schema`
  fails if any telemetry field is ever added to the output contract. A sub-agent has no
  field to report one in, and `additionalProperties: false` rejects any it invents.
- HONEST FAILURE: a `failed` return is telemetered too — cost is incurred whether or not
  the work succeeded, and a failure logging no cost would make runs look cheaper than they
  were. Distinguishability is carried by `status`; the orchestrator branched on it alone,
  parsing no prose.
- GRACEFUL DEGRADATION: absent or partial `model_usage` yields a zeroed `Usage` rather than
  raising. Missing telemetry must never fail a delegation that succeeded, and pre-telemetry
  logs in `.runs/` stay readable.
- NEXT → Stop 2

## STOP 2 — Gate at the invocation boundary — MET 2026-07-29
The original STOP 2 was mostly about a codebase that is not this one — see CUT. What
survives is the real hole it pointed at: `gates.check()` reads the brief's **declared**
`approval_gates_touched` (`gates.py:45-66`), so a brief whose objective is "deploy to prod"
but which declares `none` passes untouched.

**OPERATOR RULING — the enforcement model, verbatim:**
> The overlay must not ask the model "is this risky?" — that rebuilds the bypassable
> guardrail.
> - Gate keys off the observed tool/target being invoked, via a static tool→class map in
>   code, at the invocation boundary. Not off the model's description of its own intent.
> - Classes: `money | prod | permissions | public | irreversible` → require approval before
>   execution.
> - Fail closed: unknown or missing class → require approval. Never default to safe.

This settles the tension that blocked the stop. Neither option originally on the table was
right: cross-checking prose *is* asking a model about intent, and leaving the declaration
load-bearing lets a mis-declared brief run. Keying off the observed invocation removes the
model from the decision entirely.

- [x] Static `TOOL_CLASS` map in code: tool/target → one of `money | prod | permissions | public | irreversible` — `gates.GateClass` + `gates.TOOL_CLASS`
- [x] Enforce at the invocation boundary, before execution — not at brief-validation time — `gates.require_approval`, called from the four `meta_client` writes before any request is built
- [x] Fail closed: an unmapped tool or a missing class requires approval. No default-safe branch, and no "unknown means fine" path — unmapped raises with class `unclassified`
- [x] Keep the existing declared-gate pre-flight check (`gates.enforce`) as well. The two are different enforcement points, not competing ones: the declaration halts before spend, the tool→class map is the runtime backstop that cannot be talked past. Removing the pre-flight would trade a cheap halt for an expensive one.
- [x] Declaration is ADD-ONLY — `gates.effective_class` unions declaration and map, and the map always wins. Declared-safe cannot downgrade a classed target.
- [x] Tests: `tests/test_invocation_gates.py`, 22 tests
- DONE-WHEN: approval is required for every mapped class and for every unmapped tool, decided from the invocation and not from any model's description of it; a declared-`none` brief cannot reach a gated target.

**Verified 2026-07-29.** Suite 109 → **131 passed, 15 subtests**; `mastery check` exit 0.

- CLASSES ASSIGNED: `publish_ig_post` → `public`, `publish_page_post` → `public`,
  `reply_to_comment` → `public`, `delete_comment` → **`irreversible`** (not `public`:
  classing deletion as publishing would let a publishing approval cover a destructive act,
  and the harm here is that it cannot be undone).
- ONE VOCABULARY: the six CLAUDE.md declaration keywords are aliased onto the five classes
  in `GATES` rather than kept as a second set — otherwise a `production` declaration
  reaches no `prod` class and silently clears. `paid-tool` classes as `money`, since a
  metered API is spend.
- FAIL-CLOSED LIVES IN ONE PLACE: `classify()` reports what the map says and nothing more;
  `require_approval()` owns the decision that unknown ⇒ halt. Callers cannot each get it
  slightly wrong.
- `ApprovalRequired` subclasses `GateHit`, so every existing `except GateHit` path already
  halts on it. Widening a guardrail must not require callers to opt in.
- WHY THE OLD HALT WASN'T GOOD ENOUGH: `NotImplementedError` is fail-closed *by accident* —
  it halts because nobody wrote a body, so it disappears the day someone does. The halt is
  now about what the method **is**. `test_no_write_raises_notimplementederror_any_more`
  pins that. When a body is written it goes *after* the check, and the check stays.
- NO INTENT INPUT EXISTS: `require_approval` takes a target and an optional declaration.
  There is no argument, and no combination of arguments, that returns without raising —
  approval arrives as a fresh operator request, never as a flag this process sets on itself.

**Scope note for whoever implements this.** The invocation boundary is not one place:
- SDK tool calls — currently moot by construction. `config.delegation.denied_tools` hard-denies `Agent`, `Bash`, `Write`, `Edit`, `NotebookEdit`, and `permission_mode="dontAsk"` refuses anything not pre-approved, so the sub-agent tool surface is read-only today. The map still gets built, because it must already exist the day a write tool is granted.
- `integrations/` method calls — this is where the rule bites *now*. `meta_client.publish_ig_post` / `publish_page_post` / `reply_to_comment` / `delete_comment` are the real gated targets (`public`, `public`, `public`, `irreversible`). They currently `raise NotImplementedError`, which is fail-closed by accident; this stop makes it fail-closed on purpose, by class.
- Supabase writes, *if* the Supabase state-layer path is resumed — `permissions` for schema/RLS changes, `irreversible` for deletes. Note Stop 4 landed as a read-only Postgres projection instead, which has no sub-agent write path, so this target does not exist today.
- NEXT → Stop 4

## STOP 3 — Routing as pure code — MET
- [x] Route selection is deterministic code, zero LLM calls
- [x] `roster.py` validates the selected name
- EVIDENCE: on the `mastery run` path the brief names the agent and `roster.get()` validates it (`roster.py:114-126`), raising `RoutingError` on anything not in the roster — no model call. The drafter also validates model-proposed routes in code (`drafter.py:161-163`). The only LLM routing anywhere is `mastery draft`, which by design proposes and never runs, and whose output the operator edits before it executes.
- CONSIDERED AND REJECTED: converting the drafter to first-match keyword matching. The drafter also writes objectives, success criteria, and out-of-scope text; keyword matching cannot produce those. Zero-token routing is already true on the path that actually executes work.

## STOP 4 — Queryable run warehouse — MET 2026-07-30, narrower than specified
**Read this before crediting the stop.** What shipped is a **queryable warehouse**: every
run log mirrored into Postgres as verbatim `jsonb`, idempotent ingest, and views that join
cost and quality by `task_id`. What was *originally specified* — a persistent state layer
whose headline guarantee was "a repeat claim reuses a stored verdict instead of recomputing"
— **did not ship and is not built.** The two are not the same thing and the second does not
follow from the first. See "What is NOT built" below before assuming otherwise.

Two divergences from the 2026-07-29 approval, both deliberate, both recorded here rather
than quietly absorbed:

- **Postgres, not Supabase.** The store is self-hosted Postgres 16 on the DigitalOcean
  droplet, not a Supabase project. Conditions 1 and 2 below were written for the Supabase
  path; they are therefore **neither satisfied nor violated** — they are unexercised. If
  Supabase is still wanted as the state layer, both conditions remain open as written.
- **A projection, not a state layer.** The warehouse is downstream-only. Nothing in the
  orchestrator imports `warehouse.py`, `psycopg` is absent from `requirements.txt`, and
  ingest is an explicit `mastery ingest` — so the system runs unchanged with the database
  down or absent. That is the design (JSONL stays the source of truth; a local append has
  no network failure mode), and it is also precisely why this cannot serve claim reuse as
  built: nothing reads from it on the run path.

**Shipped:**
- [x] Runs mirrored to a queryable store — `events (run_id, seq, ts, event, task_id, payload jsonb)`, payload a faithful copy of the logged record
- [x] Idempotent ingest — `(run_id, seq)` primary key with `ON CONFLICT DO NOTHING`; `seq` is the line number, so re-ingest of an unchanged log inserts zero rows
- [x] Cost and quality views joinable by `task_id` — 9 views; `v_stage_cost` sums delegation + verdict + quality into `total_cost_usd`
- [x] Crash visibility — `v_open_delegations` surfaces a `delegation_start` with no matching end
- [x] Malformed lines named, not swallowed — reported by file and line; one torn line does not cost the rest of the run
- EVIDENCE: `mastery/warehouse.py`, `scripts/postgres_schema.sql`, `scripts/provision_postgres.sh` (idempotent, carries the grants fix), `mastery ingest` in `cli.py`. 16 unit tests in `tests/test_warehouse.py` cover log→rows without a server and deliberately import no psycopg. `scripts/check_warehouse.py` covers the half that cannot be faked — 22 assertions against a live server, including "second ingest inserts zero rows" and `v_stage_cost` summing 0.25 + 0.05 to **0.30**, proving verdict cost is not dropped.
- RE-VERIFIED 2026-07-31 on clean infrastructure. The predecessor droplet was destroyed and a fresh one (`masteryOS`, id 588880069) provisioned from zero. Pre-flight confirmed the rebuild actually took — new host key, 12-minute uptime, all eleven predecessor artifacts absent — after an earlier teardown had been reported complete and silently had not. `provision_postgres.sh` ran clean from a bare Ubuntu 24.04 box (its first ever from-zero run, so the "works on a rebuilt droplet" claim in its header is now tested rather than asserted), applied the grants block, and was a no-op on re-run. All 22 live assertions pass against the new server, including a second ingest inserting 0 rows and `v_stage_cost` returning 0.30 against a delegation figure of 0.25. Credentials regenerated on-box at mode 0600; Postgres bound to 127.0.0.1 only. The check was run over an SSH tunnel from the repo — nothing was copied onto the droplet.

**What is NOT built — do not credit these:**
- [ ] Claim-level verdict reuse — a repeat claim does **not** reuse a stored verdict; it recomputes every time. Nothing hashes claims, nothing reads the store on the run path. This is the original headline guarantee of the stop and it is absent. If wanted, it is a **separate future stop**, and a real one: it needs a claim-identity scheme, a staleness policy, and an honest-degradation path for when the store is unreachable — none of which the warehouse implies.
- [ ] KPI history persisted
- [ ] Reject-with-reason persisted as structured rows
- [ ] Supabase project isolation with RLS verified (Condition 1 — unexercised, see above)
- [ ] Service-role key at `~/.config/mastery/supabase.env` (Condition 2 — unexercised, see above)
- [ ] Writes classified against the Stop 2 tool→class map — not yet needed: the warehouse has no write path from a sub-agent, and `mastery ingest` is operator-invoked
- DONE-WHEN (**met, as rewritten**): runs are mirrored to a queryable store; ingest is idempotent under repeat runs; cost and quality views are joinable by `task_id`; and the orchestrator still runs with the store absent.
- DONE-WHEN (**original, not met**): a repeat claim reuses a stored verdict instead of recomputing; a rejection writes a queryable row; agent state is provably in its own project/schema with RLS on.
- NEXT → Stop 7 (Stop 6's second half is blocked behind Stop 7 — see below)

---

### Original approval record — the Supabase state-layer path (unexercised)
Retained because the approval and its conditions still stand if that path is resumed.

Authorized as the state layer. Rationale recorded: Supabase is already in-stack, so this is
an authorized dependency, not a silent paid failover — it does not trip the "no silent
billable fallback" rule.

**Condition 1 — isolation.** Mastery OS gets its **own dedicated Supabase project**,
reserved for the governor. RLS on.

Stated positively and self-standing, corrected 2026-07-30. It previously read "separate
project, or at minimum a separate schema, from FaithFeed prod", which was wrong twice:

- It defined the governor's own requirement *relative to a vertical* — the same defect
  logged in BACKLOG about `pipelines.py`. The governor's store is its own because it is the
  governor's, not because of what else exists in the account. The requirement holds if
  every other project is deleted tomorrow.
- **The schema fallback was unsafe and is removed.** A Supabase service-role key is scoped
  to the *project* and bypasses RLS. A schema-level split sharing one project would hand
  the governor's key full read/write over everything else in that project, so Condition 1
  and Condition 2 contradicted each other. Schema separation is not a weaker version of
  project separation here; it is not isolation at all.

Naming: do not name the project after a vertical. It is the governor's store.

**Account state as of 2026-07-30** (read-only check, nothing created): org
`efufvmgzgxnlkpelrilg` (LMW-Labs's Org) holds four projects — `himsportsgroup`
(ACTIVE_HEALTHY), `faithfeedAI` (INACTIVE), `hodge_performance` (INACTIVE), `lmwlabs-web`
(INACTIVE). No governor project exists. A new project costs **$0/month**.

**Open question before this stop starts — free-tier auto-pause.** Three of four existing
projects are already INACTIVE. A paused project means the state layer is unavailable, which
breaks this stop's own DONE-WHEN: a repeat claim cannot reuse a stored verdict from a
database that is asleep. Decide whether the governor's store can tolerate pausing (and the
orchestrator must then degrade honestly rather than silently recompute), or whether it needs
to hold an always-on slot. This is a design decision, not a detail — a state layer that
silently vanishes and gets silently recomputed is the fabricated-success failure mode
wearing a different hat.

**Condition 2 — credentials.** Service-role key handled per the credential decision from
the hermes thread. **RESOLVED:** the hermes `.env` turned out to be byte-identical to
`.env.example` — zero secrets, nothing to inherit. So there is no hermes pattern to adopt,
and the pattern to use is the one this project already established for Meta:
`~/.config/mastery/<name>.env`, `chmod 600`, read via `os.environ` at the chokepoint, never
committed, never passed into a brief payload. A service-role key bypasses RLS, so it is
operator-only and must never reach a sub-agent's context.

If this path is resumed, the outstanding items are the unchecked boxes recorded above under
"What is NOT built", plus a single chokepoint module in the shape of
`integrations/meta_client.py` — sub-agents call methods, never see the key, never build
queries — and the requirement that the service-role key stay absent from the repo and from
every brief payload.

## STOP 5 — Manager context from state, not inline — MET
- [x] Manager does not carry all returns inline across stages
- [x] Manager window does not grow with stage count
- EVIDENCE: every delegation and every verdict is a fresh stateless `query()`; no conversation accumulates across stages. `verdict.build_prompt` receives the brief's criteria and the return only — explicitly not the context payload (`verdict.py:65-71`). Stage-to-stage carry-forward is the `BriefFactory` callback, which passes only what it chooses (`orchestrator.py:75-78`). There is no linear growth to remove.

## STOP 6 — Cache measurement (first half open) + model tiering (BLOCKED behind Stop 7)

### 6a — Cache measurement — MET 2026-07-30
- [x] Confirm from telemetry that the static prefix is served from cache
- EVIDENCE: four live runs, **617,393 cache-read tokens against 182,860 cache-creation** — a 3.4:1 read-to-create ratio. The prefix is cached, not re-billed per call. Fell out of Stop 1's fields at no extra cost, as predicted.
- DONE-WHEN: one run's telemetry shows the cache split. Stop 1 already emits both fields.
- CUT: "prompt-cache static prefix." `ClaudeAgentOptions` exposes no `cache_control` knob; the CLI manages caching. Nothing to implement — only something to measure.

### 6b — Model tiering — APPROVED 2026-07-29, and BLOCKED until Stop 7 is MET
Approved, scoped, and dependency-gated.

**HARD DEPENDENCY:** stays BLOCKED until Stop 7 (eval loop) is MET. Operator's reasoning,
recorded because it is the whole point: *dropping to cheap tiers without the eval loop
trades measured cost for unmeasured quality loss — that's the dishonest-success failure
mode. Eval first, then tier.* Do not start 6b to "get ahead" while Stop 7 is open; a cost
win that cannot be checked against a quality baseline is not a win, it is an unmeasured
regression that looks like one.

- [~] BLOCKER: Stop 7 MET, with a quality baseline recorded on the strong model **before** any role is tiered down — **partially satisfied 2026-07-31, and the gap is the interesting part. Read below before treating this as clear.**

**What was found when this blocker was actually checked, rather than assumed from "Stop 7 is MET".**
Stop 7 being MET satisfies the *letter* of this blocker. It did not satisfy the substance.
Baselines existed for `researcher` and `content` only — **neither of which 6b proposes to
tier**. The three roles it does target had no baseline at all:

| Role 6b would tier down | Baseline as of 2026-07-31 |
|---|---|
| fact-check retrieval (`fact-checker`) | none — its only run returned `blocked`, and blocked outcomes are never scored |
| verify-only (`delegate.run_verdict`) | **none, and not obtainable this way** — the manager verdict is control flow, not a rubric-scored output |
| validation | none — schema validation is code, with no model call to tier |

So starting 6b would have tiered exactly the roles whose quality could not be compared to
anything, which is the failure the operator's own blocking note describes.

**`fact-checker` baseline recorded 2026-07-31.** Three briefs
(`20260731-rd-004/005/006`) with drafts that are genuinely well-sourced — the inverse of
the gate test. All three returned `partial` ("publishable with corrections"), all three
were accepted by the manager, all three were scored. n=3, matching the existing baselines'
shape. $1.04 total.

**The baseline is at the ceiling, and that is a weakness, not a result.** 3.0/3 on every
dimension of every run — 15 of 15 anchors at maximum, zero variance. It is *sufficient for
detecting regression*, which is literally what 6b's DONE-WHEN asks, so it does unblock
that. It is **not** sufficient to show the rubric discriminates at all. If a cheaper model
also scores 3.0 on these tasks, that result is uninterpretable: it cannot distinguish "the
cheap model is just as good" from "this rubric cannot tell them apart at this difficulty."
The cause is task design — sources supplied in the payload, short drafts, unambiguous
defects. Before the tiering comparison is run, the baseline set needs harder cases with
observed spread, or the comparison proves nothing.

**Two smaller findings from the same runs.** `fact-checker` returned `partial` even on the
draft written to be fully clean: it found an *implied* comparative claim nobody planted —
that juxtaposing our 22% against a 19% category average asserts a like-for-like comparison
the two sources do not establish are methodologically comparable. Worth knowing that this
agent will rarely return `complete` on real promotional copy. And the recorded model string
is `claude-haiku-4-5+claude-sonnet-5`, the joined usage names, same as the existing
baselines — comparability holds, but the label is muddier than "strong model" implies.

- [ ] REMAINING BLOCKER: decide how verify-only quality is measured before tiering it. It has no rubric and is not an agent output; the honest measure is verdict *agreement* against the strong model on the same returns, which is a different mechanism than this stop currently assumes.
- [x] ~~REMAINING BLOCKER: a gate agent's quality cannot be measured by the current eval loop at all.~~ **Fixed 2026-07-31** — gate closures are now scored; see the BACKLOG entry. The measurement can now reach a gate's actual work.
- [x] ~~REMAINING BLOCKER: **no observed score variance anywhere.**~~ **Resolved 2026-08-01 by calibration rather than by sampling.** Every `fact-checker` score on record is still a 3, and that is no longer the objection it was.

  The blocker's real content was that a flat result is *uninterpretable*: it cannot distinguish "the cheap model is just as good" from "this rubric cannot tell them apart." Waiting for a non-3 to appear was the wrong remedy — if the instrument were broken, more runs would return 3.0 and read as confirmation. Sampling cannot audit the instrument doing the sampling.

  `scripts/probe_grader.py` calibrates it directly. Four synthetic `fact-checker` returns on one fixed brief, each written against a named row of the rubric's own anchor text — a 0, a 1, a 2, a 3 — graded over the real `run_grader` path. Result: **0.2 / 0.6 / 1.2 / 3.0, monotonic, spread 2.80 on a 3-point scale.** The rubric discriminates, and STOP 6b's comparison is now interpretable: a cheap model scoring 3.0 means it is genuinely as good on these tasks, because the instrument demonstrably registers a drop when there is one.

  **The grader runs strict, not lenient** — the opposite of the failure mode suspected. It scored *below* intent on both middle rungs, and reading the justifications, it was right and the rung labels were generous: it caught that rung-2's correction appended "the sharpest decline the series has recorded" with nothing supporting it, and that rung-2 rated the superlative `PARTIALLY SUPPORTED` on outside knowledge the supplied source did not contain. Both were deliberately planted; neither was described to the grader.

  Consequence for the existing baseline: the 15-of-15 maximum in `evals/baselines.json` is now positive evidence about the agent rather than an unread dial. A strict instrument returning 3.0 means the work was good.

  Nothing from the probe is written to the run log — synthetic scores would corrupt the trend they exist to audit, so it drives the runner directly and never touches `Orchestrator` or `runlog`.

- [x] ~~REMAINING BLOCKER: the ladder covers `fact-checker` only.~~ **All 17 ladders written and run 2026-08-01. 16 pass, 1 fails.** `mastery check` reports `16/17`.

**The one failure is the most valuable result here.** `content` came back `[1.5, 1.25, 2.75, 2.5]` — **not monotonic**: the rung built to be a 0 outscored the rung built to be a 1, and the rung built to be a 3 scored *below* the rung built to be a 2. `set_baseline` refuses on it, and `content` is one of the two agents that already had a grandfathered baseline. That baseline is now known to rest on an instrument that does not order its own anchors.

What I cannot say is *why*, and I am not going to guess: it is either the rubric failing to discriminate, or my ladder being badly built for it — plausibly the 0-rung, which is a competent post on the wrong angle and may be earning hook and CTA credit the anchors do not intend. Distinguishing those needs a second ladder, not an opinion. **Open, and assigned to nobody yet.**

Two mechanical near-misses worth recording, because both were caught by machinery rather than by care:

- **The 4-digit task-id ladders never spent anything.** `ui-ux`, `data-model-agent` and `metrics-agent` were written with labels like `rd-1000`; `brief.build` rejects `NNNN`, so all three failed *before* the first grader call. The `rd-9xx` block was also nearly exhausted, so the remaining ladders moved to the `ff-9xx` and `ops-9xx` verticals.
- **`UnicodeEncodeError` cost 8 grader calls, and it was a known bug in a new place.** `probe_grader.py` is a second entry point that never went through `cli.main`, so it never called `_force_utf8_stdio()`. Any grader justification containing `→` killed the script *after* all four calls were paid for — precisely the failure `cli.py`'s own docstring describes ("the work is done… and then thrown away at the last step"). Two ladders lost that way. Fixed by importing the existing guard rather than reimplementing it, since a duplicate is what would let the two drift.

**What it actually cost, measured not estimated.** Cost telemetry was threaded into `CalibrationResult.per_rung` *before* these runs, specifically so this number would exist:

| | |
|---|---|
| Recorded total, 68 priced calls | **$3.632134** |
| Per ladder | min $0.175126, max $0.261709, mean $0.213655 |
| Per call | min $0.0256156, max $0.0933757, mean $0.0534137 |
| Unpriced calls | ~16 (two pre-telemetry `fact-checker` runs, two crashed runs) |
| Honest total | **≈$4.48** — the unpriced calls are ~$0.85 at the observed mean and cannot be recovered exactly |

**The earlier projection was high, and its stated caveat was the reason.** Pricing from four real `fact-checker` grader calls projected $4.78–$5.91 for 64 calls, point $5.38. Actual for the 16 new ladders was ≈$3.42. The flagged reason was correct: `fact-checker` has the largest rubric of the seventeen, so it was the top of the range rather than a representative unit. The proxy per-call mean ($0.08409565) over-stated the real one ($0.0534137) by about 57%, because those proxy calls graded real agent returns rather than ladder rungs.

**Calibration is a standing per-rubric obligation, not a one-time gate — enforced 2026-08-01.** The operator's framing, and it is the right one: a pass for `fact-checker` says nothing about the other sixteen, which have different dimensions, different anchors, and different failure modes.

| Piece | Where | What it does |
|---|---|---|
| Ladders as data | `docs/agents/calibration_ladders.md` | one brief + one return per level, per rubric. Adding a role is writing data, not editing code |
| Trust state | `mastery/calibration.py` | `calibrated` / `missing` / `stale` / `failed`, keyed `(agent, rubric_version)` |
| The refusal | `evals.set_baseline` | raises `Uncalibrated` unless a passing ladder exists for that exact version |
| Visibility | `mastery eval`, `mastery check`, `probe_grader.py --status` | uncalibrated groups are marked inline; coverage is printed as `n/17` |
| Recording | `probe_grader.py --record` → `evals/calibration.json` | passes **and failures** stored |

Four decisions worth stating, because each had a plausible alternative:

1. **It binds baselines, not delegations.** An uncalibrated rubric still runs and still scores — scoring stays write-only and observational, and `status` remains the only thing the orchestrator branches on. Halting real work over an unwritten ladder would make an uncalibrated rubric *worse than no rubric*, which would push people to delete rubrics to get their work done. A baseline is the artifact that gets trusted, so that is where the refusal belongs.
2. **It is version-bound, and that is the trap the whole thing turns on.** A ladder is written against specific anchor text. Edit the rubric and the rungs claim levels that no longer exist, so a calibration that silently carried across a version bump would be *worse* than none — it would attest to markings nobody had checked. `status` returns `stale` and the refusal stands. Pinned by `test_calibration_does_not_carry_across_a_rubric_edit`.
3. **A failed calibration is recorded, not discarded.** Deleting it would leave the rubric merely *unmeasured* rather than *known bad*, and the next person would have no way to tell those apart.
4. **Spread alone is not a pass.** A ladder must be monotonic as well as clear `MIN_SPREAD`; a grader that separates outputs but orders them wrongly is responding to something other than the anchors.

**A real bug this shook out:** the coverage counter reported a confident `0/17` because `roster.DELEGATABLE` holds `Agent` objects while the rubric and calibration tables are keyed by name, so every lookup returned False. A counter failing exactly the way the grader it counts was suspected of failing. Fixed and pinned by `test_coverage_is_counted_by_agent_name_not_agent_object`.

**The existing baselines are grandfathered, and say so.** `researcher` and `content` have baselines recorded before this rule existed; `set_baseline` would refuse to write them today. They are kept rather than deleted — they are the real record of what was measured and when — and `evals/baselines.json` now carries a `_calibration_note` naming both as provisional until their rubric has a passing ladder.

**Reproducibility, recorded honestly:** the `fact-checker` ladder was run twice. The middle rung moved `1.2 → 1.6` between runs; the 0-rung, the 3-rung, monotonicity, and the 2.80 spread were stable. The verdict is robust; individual rung values are not exact. Worth knowing before anyone reads a single calibration number as precise.

**`content`'s ladder failed, and diagnosing it found a second axis the calibration was
never bound to. 2026-08-01.** Sixteen of seventeen ladders passed. `content` returned
`[1.5, 1.25, 2.75, 2.5]` against intended `[0, 1, 2, 3]` — spread 1.5, not monotonic. Per
dimension:

| dimension | r0 | r1 | r2 | r3 | ordered |
|---|---|---|---|---|---|
| `executes_the_given_angle` | 2 | 1 | 3 | 3 | no |
| `hook_strength` | 2 | 1 | 3 | 3 | no |
| `cta_present_and_matched` | 0 | 1 | 3 | 3 | yes |
| `declared_constraints_honored` | 2 | 2 | 2 | 1 | backwards |

**Not a bad ladder.** `quality.build_prompt` passes the grader the success criteria, the
status, the summary, the deliverables, the risks, and the rubric — deliberately *not* the
context payload, and incidentally not `constraints` either. Two of `content`'s four
dimensions ask whether the output honoured instructions that live in exactly those two
places: the angle is in the context payload, the 150-word cap is in `constraints`. Checked
directly against the rendered prompt — the angle: absent; the word limit: absent. So
`declared_constraints_honored` scoring `2, 2, 2, 1` is not noise around a signal, it *is*
noise: rung 0 violated every constraint and scored 2, rung 3 met them all and scored 1,
its honest "constraint tension" note reading as an admission. The dimension is unscoreable
by construction.

This is also why one rubric failed and sixteen passed. The other rubrics' dimensions are
self-evidencing from the output alone — *does every flag quote verbatim, does every action
state its undo, does every claim carry a link*. `content`'s are **relational**: does this
match what it was told to do. A grader denied the instruction cannot answer them.

**The fix is to show the grader the brief's constraints — and that fix would have silently
voided all seventeen calibrations.** Calibration was keyed `(agent, rubric_version)`. The
grading prompt was not in the key. Change what the grader sees and every entry on file
goes on reporting `calibrated` about an instrument that no longer exists — the exact trap
version-binding was built to catch, arriving through the one door version-binding does not
cover. Found before making the change, not after.

| Piece | Where | Note |
|---|---|---|
| The hash | `quality.prompt_fingerprint` | `_render` against fixed sentinel fixtures, sha256, first 12 hex. Currently `93d071d96c17` |
| The key | `calibration.result_key` | now `agent\|rubric_version\|prompt_fingerprint`; a mismatch on either axis simply misses |
| The verdict | `calibration.Verdict.PROMPT_CHANGED` | distinct from `STALE`: different cause, different repair |
| Visibility | `mastery check`, `probe_grader.py --status` | fingerprint printed alongside the `n/17` count |

Three decisions worth their reasons:

1. **It hashes the rendered prompt, not this module's source.** A source hash would void
   seventeen ladders over a docstring edit, and the obvious way to stop that noise would be
   to stop believing the fingerprint. Rewording the grader's instructions *does* move the
   hash, and should — that text is the grader's calibration in the ordinary sense.
2. **The rubric is passed into `_render` rather than looked up inside it**, so the
   fingerprint is independent of `quality_rubrics.md`. The two axes move separately instead
   of each dragging the other. Pinned by
   `test_the_fingerprint_does_not_move_when_a_rubric_moves`.
3. **A result with no fingerprint is refused at the write**, not tolerated and filtered at
   the read. A stored row that names no prompt is not evidence about any prompt, and every
   reader would have to special-case it forever — which is where a default of "assume
   current" eventually gets written.

**The seventeen existing entries were rekeyed onto `93d071d96c17`, not re-run. The claim is
checkable, which is the only reason it was allowed.** `mastery/quality.py` was last
committed in `98a47b9`, which predates both calibration commits, so no ladder could have
run through any other prompt; and the later split of `build_prompt` into `_render` was
verified to leave the rendered text **byte-identical for all 17 agents** before the rekey
was applied. Recorded in `evals/calibration.json` under `_fingerprint_backfill` and pinned
by `test_every_recorded_calibration_names_the_prompt_it_ran_through`.

**Verified.** Suite 204 → **210 passed**; `mastery check` exit 0, `16/17`, prompt
`93d071d96c17`. Simulating the coming change live — adding the brief's constraints to the
prompt — moves the fingerprint to `25809eb1e704` and flips all 17 rubrics to
`prompt-changed`, naming the rubric as unaffected. No spend: the fingerprint is pure
computation.

→ BACKLOG: show the grader the brief's constraints, then re-run all 17 ladders (~$4.48 at
the measured rate). Not done here on purpose — landing the mechanism first is what makes
that change *visible* rather than silent, and the re-run is real spend that is the
operator's to authorise.

**A harder baseline set was attempted 2026-07-31 and produced ZERO scores. That is the
finding.** Three cases built to need reasoning rather than pattern-matching: a survey figure
from a self-selected in-app sample projected onto the whole account base; a preprint cited
as peer-reviewed whose authors explicitly disclaim causation; and two correct subgroup
retention figures compared causally, with a planted contradiction between the sources
(0.22×34 + 0.78×12 = 16.84%, against a stated overall of 22%).

`fact-checker` handled them well. It caught the selection-bias projection, caught the
preprint mislabelling *and* the completers-only sample *and* the self-report measure, and
on the third produced a report the manager twice returned as `revise` for
self-contradiction — which is the verdict loop working, then failing honestly at the retry
cap.

None of it was scored:

| Case | Outcome | Scored |
|---|---|---|
| rd-007 selection bias | `blocked` (not publishable) | no |
| rd-008 preprint / causation | `blocked` (not publishable) | no |
| rd-009 contradictory sources | `partial` → `revise` ×2 → `failed` | no |

**Why, in code.** `orchestrator.py:261` scores only on `Verdict.ACCEPT`, and `blocked`
short-circuits before a verdict is requested at all. The rationale is written in the
comment: *"Grading a failed or halted return would score work that is not being used, and
would bias the trend with attempts nobody kept."* That is correct for `failed`. **For a
gate agent it is backwards.** A gate's `blocked` is not unused work — per the status table
in CLAUDE.md, `blocked` is how a gate returns *closed*, which is its most valuable output.
The rule was written treating `blocked` as "did not finish"; for `qa`, `fact-checker`,
`risk-review`, and `legal-review` it means "finished, and the answer was no."

**The consequence for this stop.** A gate agent can only ever be scored on inputs it did
*not* need to stop — the cases where it had least to do. The 3.0/3 ceiling on the easy set
is therefore not an artefact of my task design; it is structural. Every discriminating
input is censored out of the sample by construction. 6b's DONE-WHEN — *"quality scores
after tiering are compared against the pre-tiering baseline and do not regress"* — is
**not achievable as written for `fact-checker`**, because the comparison can never reach
the behaviour that matters. Tiering a gate down on the strength of a baseline built only
from its easy cases would be a measured cost win against an unmeasurable quality risk,
which is the precise thing this stop was blocked to prevent.

`roster.py` already carries `is_gate` on every agent, so the distinction needed to fix this
exists in code today. → BACKLOG: score gate closures.
- [ ] Tier DOWN mechanical roles only: validation, verify-only (`delegate.run_verdict`), fact-check retrieval
- [ ] Keep judgment and synthesis roles on the strong model: `risk-review`, `legal-review`, `strategy`
- [ ] Routing needs no tier — it is already code and spends no tokens (Stop 3 MET)
- [ ] Rewrite `CLAUDE.md:190` to scope the strong-model mandate to judgment roles rather than reversing it blanket — see the exact quote and proposed wording below
- [ ] `delegation.model` becomes per-role; `config.py:76-79` comment updated in the same commit
- DONE-WHEN: telemetry shows the correct tier per call; every judgment role is provably still on the strong model; quality scores after tiering are compared against the pre-tiering baseline and do not regress.

**The line to be rewritten, quoted exactly as it stands today:**

`CLAUDE.md:190`:
> `- There is no per-role model routing; `delegation.model` is global.`

`mastery/config.py:76` (the docstring on `Delegation`, which must move with it):
> `    CLAUDE.md: no per-role model routing; `delegation.model` is global.`

Proposed replacement for `CLAUDE.md:190`, scoped rather than reversed — **not yet applied,
pending your sign-off on the wording:**
> `- Model routing is per-role and scoped by kind of work, not global. Mechanical roles —`
> `  validation, verify-only manager invocations, fact-check retrieval — may run on a cheaper`
> `  model. Judgment and synthesis roles — `risk-review`, `legal-review`, `strategy` — run on`
> `  the strong model, and tiering one down is a change to this file, not a config tweak.`
> `  No role may be tiered down before the eval loop can show its quality did not regress.`

The last sentence is what keeps the scoping from eroding later: it puts the Stop 7
dependency in the governing doc rather than only in this ledger.
- NEXT → Stop 7

## STOP 7 — Output-quality eval loop — MET 2026-07-30
- [x] Score output quality per run (not just orchestration mechanics)
- [x] Log scores so they trend run-over-run
- [x] Record a baseline on the strong model before anything is tiered
- [x] Four pins present and failing-on-bypass
- DONE-WHEN: each run emits a per-role quality score joined by `task_id`; scores queryable and trending; fresh strong-model baseline recorded before any Stop 6 tiering; scoring path telemetered with its tier declared; four pins green.

**Verified 2026-07-30.** Suite 132 → **164 passed, 15 subtests**; `mastery check` exit 0.
Four live runs, $1.9184 total; grading is 14.2% of that.

FRESH BASELINE (`fresh-strong-model`, model `claude-haiku-4-5+claude-sonnet-5`, rubric v1):

| agent | n | mean | per-dimension |
|---|---|---|---|
| researcher | 3 | **2.75/3** (91.7%) | source_primacy 3.0 · question_coverage 3.0 · evidence_inference_separation 2.667 · citation_traceability 2.333 |
| content | 1 | **2.75/3** (91.7%) | executes_the_given_angle 3.0 · cta_present_and_matched 3.0 · declared_constraints_honored 3.0 · hook_strength 2.0 |

RETRO SANITY CHECK (`retro-sanity-check`, NOT a baseline, stored separately):

| agent | n | mean | divergence from fresh |
|---|---|---|---|
| researcher | 3 | 2.5/3 (83.3%) | **+0.250** fresh is higher |
| content | 2 | 3.0/3 (100%) | **−0.250** retro is higher |

Divergence is real and is surfaced, not averaged away. Reading of it:
- `researcher` fresh scores higher on `source_primacy` (3.0 vs 2.0) — the fresh briefs
  demanded Meta-owned sources explicitly, and the bounded scope let the agent reach them.
  This is largely brief quality, not model quality.
- `content` retro scores *higher* on `hook_strength` (3.0 vs 2.0), which is the honest
  direction: the fresh content brief forbade emoji and capped hashtags, and the grader
  judged one hook weaker under those constraints.
- Both retro sets are graded from the run log's already-summarised reconstruction of the
  return, not the live return, so they are systematically not like-for-like with fresh.
  That is exactly why they carry their own label.

- CACHE EVIDENCE (satisfies **Stop 6a**): across the four live runs, 617k cache-read tokens
  against 182k cache-creation. The static prefix is being served from cache, not re-billed.
- MULTI-MODEL FOLD VALIDATED: every live call reported `claude-haiku-4-5+claude-sonnet-5` —
  the SDK really does use two models per delegation (haiku for WebFetch summarisation). The
  decision in Stop 1 to sum across models and join their names, rather than pick one, was
  load-bearing after all; picking one would have under-reported every run.
- GRADER VARIANCE OBSERVED: `20260729-rd-007` was run twice (operator error, see below) and
  scored 2.75 both times but with **different dimension splits** — once
  `citation_traceability=2, evidence_inference_separation=3`, once the reverse. Same
  aggregate, different path to it. Worth knowing before treating any single dimension as
  precise, and an argument for n>1 in any baseline.

**Known weakness, stated plainly:** `content`'s baseline is n=1 and `researcher`'s is n=3
with two of those from the same brief. That is a thin baseline. Before Stop 6b relies on
it, it wants a few more runs across different briefs — otherwise a tiered-down run that
scores 2.5 cannot be distinguished from ordinary variance.

**Operator error to record:** `briefs/20260729-rd-007.json` was executed twice, because the
command that ran it was piped to `head` and then to `tail` in the same shell line, which
re-invoked it. Cost ~$0.35 of unintended spend. No guardrail failed — the run was legitimate
and the cap was not reached — but it is logged because the ledger is supposed to be honest
about what happened.

**Deviation from the approved scope:** five rubrics, not three. `mobile-dev` and `qa` were
added because the RELEASE pipeline is `mobile-dev → qa` by definition, so fail-closed would
otherwise have made that pipeline unrunnable and its guardrail tests unwritable. The
remaining twelve agents fail closed as intended.

## DECISION GATE — auth mode — MET, and already passed in practice
- [x] Auth mode chosen and hardwired
- EVIDENCE: `config.py:111-160`. `mode` defaults to `"subscription"`; that path asserts `ANTHROPIC_API_KEY` is absent and raises if it is set, because a set key would silently shadow OAuth and bill the API account. `api_key` mode is available and crosses the money gate deliberately. No runtime ambiguity.
- NOTE: this gate was positioned "before first live run." Live runs already happened — see Stop 8 — so it confirms what is already running rather than preventing it. Nothing further unless the answer changes.

## STOP 8 — First live run (staged) — MET
- [x] Researcher, stateless, output hand-carried between stages
- [x] Telemetry captured; no guardrail bypassed
- EVIDENCE: five completed live delegations in `.runs/`, with real spend — researcher 30 turns/$1.43 (`d37cd84fe3bf`), 26 turns/$1.26 and 25 turns/$0.92 (`436effa2eec8`), 21 turns/$0.91 (`4457b266f514`), content 2 turns/$0.36 (`06f584d92f4d`). ~$5.19 recorded total. `permission_denials` empty on every one — no sub-agent reached outside its allowlist.
- NOTE: what those runs did NOT record is token counts or the cache split, because nothing captured them. That gap is Stop 1, and it is why Stop 1 is first.

---

## DECISIONS — all three resolved 2026-07-29
1. **Gate enforcement — RESOLVED.** Not prose cross-checking. Keys off the observed
   tool/target at the invocation boundary via a static tool→class map in code; classes
   `money | prod | permissions | public | irreversible`; fail closed on unknown or missing
   class. Full ruling recorded in Stop 2. Stop 2 UNBLOCKED.
2. **Model tiering — APPROVED, scoped, and dependency-gated.** Mechanical roles tier down;
   judgment roles stay strong; `CLAUDE.md:190` gets scoped, not reversed. **Blocked until
   Stop 7 is MET.** Recorded in Stop 6b, with the current CLAUDE.md line quoted verbatim
   and the proposed replacement awaiting sign-off on wording.
3. **Supabase — APPROVED** as an in-stack authorized dependency, subject to isolation
   (separate project/schema from FaithFeed prod, RLS on) and credential handling
   (`~/.config/mastery/supabase.env`, `chmod 600`, never in a brief payload). Recorded in
   Stop 4. Credential condition's upstream dependency is resolved: the hermes `.env` held
   no secrets.

## Open items not owned by a stop
- **CLAUDE.md:190 rewrite wording** — proposed in Stop 6b, awaiting operator sign-off. Not
  urgent: 6b is blocked behind Stop 7 regardless.
- **hermes removal** — in progress; see the environment note below.

## Environment note — hermes (2026-07-29)
Not a Mastery OS stop, but it touched this repo's interpreter resolution, so it is recorded.
`C:\Users\awyri\AppData\Local\hermes` (2.6 GB) had **two entries at the front of the
persistent user PATH**, including `hermes-agent\venv\Scripts` — which is what shadowed
`python` and made the test suite appear unrunnable earlier tonight.

- DONE: both entries removed from `HKCU:\Environment` PATH (23 → 21 entries); prior value
  backed up to `~/.config/hermes-salvage/user-PATH-before.txt`.
- DONE: standalone `uv` installed via winget (`astral-sh.uv` 0.11.32) and on user PATH.
  hermes's bundled `uv.exe` had been the **only** uv on the machine.
- DONE: `auth.json` salvaged to `~/.config/hermes-salvage/` — it holds a `credential_pool`
  with one `copilot` and one `anthropic` entry, `active_provider: "None"`.
- FINDING: the 23,865-byte `.env` was byte-identical to `.env.example`. Zero secrets. This
  is what resolved Stop 4's credential condition.
- BLOCKED on operator: three live `uv.exe` processes from `hermes\bin`, parented to
  `claude.exe`, are running Claude Desktop MCP extensions (`windows-mcp`, `blender-mcp`,
  `tooluniverse-mcp`). Deleting the directory requires killing them, which stops those
  three extensions until Claude Desktop is restarted on the new uv.

## CUT from the original ledger, with reasons
- **`Developer` / `Designer` name reconciliation.** Those strings appeared in exactly one
  file in this repo — this ledger. Zero occurrences in `mastery/` or `docs/`. The roster
  and the rubric already agree on `mobile-dev` and `ui-ux`.
- **"13 unreachable agents."** All 17 delegatable agents appear in
  `manager_decision_rubric.md:45-63`, verified programmatically against
  `roster.DELEGATABLE`. There are no unreachable agents.
- **"Move approval/risk to an overlay evaluated BEFORE routing."** Already before
  routing: rubric Step 1 precedes Step 3, and `gates.enforce` runs before the delegation
  is logged or sent (`orchestrator.py:109-119`).
- **"Non-short-circuiting" gates.** `gates.py` halts hard and deliberately has no
  `approve()` function; approval arrives as a fresh operator request, not a flag a run
  sets on itself. Non-short-circuiting evaluation means continuing past a gate, which
  weakens the guardrail. If the intent was "report every gate a brief touches, not just
  the first match," that is a smaller and better change — logged in BACKLOG.
- **STOP 1's `success` rename.** The code, CLAUDE.md, every brief in `briefs/`, and the
  test suite all use `complete` (`schema.py:36`). Superseded by the operator's own edit.
- **STOP 1's "failed produces structurally different output."** All four statuses share
  identical required fields, so adding fields to every status makes success and failure
  *more* alike. Real structural divergence needs conditional `if/then` schema, and since
  the orchestrator branches on `status` alone (`schema.py:52-57`), it would buy nothing.
  Distinguishability is carried by the `status` value itself.

## APPENDIX — Guardrail surface, as verified 2026-07-31

Audited by reading the code, not this ledger. Recorded here so the next person asking
"can a sub-agent run rogue?" gets file and line rather than reassurance.

**What is enforced.** All four are passed explicitly to `ClaudeAgentOptions` at
`delegate.py:236-240`. None is inferred, and none depends on a turn budget.

| Enforcement | Where | Effect |
|---|---|---|
| `denied_tools = ("Agent", "Bash", "Write", "Edit", "NotebookEdit")` | `config.py:88` | No spawning (spawn depth 1 is real), no execution, no filesystem mutation |
| `permission_mode = "dontAsk"` | `config.py:94` | Load-bearing. The SDK advertises ~26 tools regardless of `allowed_tools`; anything not pre-approved is refused **at call time** |
| `setting_sources = ()` | `config.py:108` | CLAUDE.md, project settings and user settings never auto-load into a delegation |
| `allowed_tools = ("Read", "Glob", "Grep")` | `config.py:83` | Read-only baseline; per-agent additions come from the roster |

`scripts/probe.py` verifies probes 5, 6 and 7 against real SDK behaviour rather than
against config values: a canary phrase that exists only in CLAUDE.md proves context
isolation, and live `Agent` and `WebSearch` attempts prove denial actually fires.

**Three qualifications. "Certain" would be the wrong word.**

1. **`config.json` can lower the floor.** `config.py:184-192` lets a config patch
   `denied_tools`, `permission_mode`, and `setting_sources` with no minimum. Setting
   `permission_mode` to `bypassPermissions` removes every protection above while
   `allowed_tools` still reads correctly. This is not a rogue-agent path — no sub-agent
   has a write tool — but it means the guarantee is *"as configured"*, not structural.
   → BACKLOG: config floor.
2. **Egress is the remaining surface.** `roster.py:84` grants researcher `WebSearch` +
   `WebFetch`; `roster.py:104` grants fact-checker `WebFetch`. Read-only is not the same
   as no-exfiltration: a prompt-injected page can induce a fetch to an attacker URL with
   brief context in the query string. Mitigated by hand-assembled minimal context and the
   60 KB cap; not eliminated. → BACKLOG: egress review.
3. **The probe is manual.** It needs a credential and makes real calls, so it is correctly
   outside `tests/` — but nothing signals when it has gone stale after an SDK upgrade.

**Coverage gap found in the same audit.** The run logs contain delegations for exactly
two agents, `researcher` and `content` (10 delegations, $6.43, zero permission denials).
`fact-checker` and `risk-review` — the two gates that can halt the Research and Debunk
pipeline — **have never executed live**. A gate that has never fired is an untested gate,
and it is the component most likely to be wrong without anyone noticing, because the happy
path never reaches it. → BACKLOG: live gate test.

## BACKLOG (log, do not action mid-stop)

### Show the grader the brief's constraints, then re-run all 17 ladders
`content`'s ladder fails because two of its four dimensions ask whether the output honoured
instructions the grader is never shown (full diagnosis under Stop 6, 2026-08-01). The fix
is to pass `brief.constraints` — and `brief.objective` — into `quality._render`.

**Pass the constraints, not the context payload.** Constraints are short and declarative;
showing them does not let the grader re-do the task or check sources for itself, which is
what the context exclusion actually exists to prevent. The exclusion stays.

**The trap to refuse:** restating the angle and the word limit inside `success_criteria`,
which *does* reach the grader. It costs nothing, makes `content` pass by tomorrow, and
leaves every real `content` run still graded blind on two of four dimensions. That is
letter-satisfaction — the same failure already recorded once in this ledger — and it would
be harder to find the second time, because the calibration would say `calibrated`.

**Consequences, both of which are the point:**
- The prompt fingerprint moves (verified: `93d071d96c17` → `25809eb1e704`), so all 17
  calibrations correctly become `prompt-changed`. Nothing silently survives.
- Re-running all 17 ladders costs **~$4.48** at the measured rate ($3.632134 recorded
  across 68 priced calls, plus ~16 unpriced early calls at the observed mean). Real spend,
  operator's call, not a side effect of a code change.

The alternative — amending `content`'s rubric to drop the two relational dimensions — is
cheaper and honest but throws away most of what "good content" means. Rejected in favour of
fixing the instrument rather than narrowing the question.

### ~~Score gate closures~~ — DONE 2026-07-31
Implemented the same day it was found. `orchestrator.py`'s `Action.HALT` branch now scores
the return when `roster.get(agent).is_gate`. Verified live: `20260731-rd-008` re-run and
scored 3/3, where the identical brief produced **no score at all** hours earlier.

**Scored, and deliberately not verified.** The operator's constraint was explicit —
*"we are not sending it back thru, it goes against the design."* So a closure gets no
manager verdict. The verdict returns accept/revise/**reject**, and a `revise` on a closure
would be a model with the power to send a gate back for another attempt that could return
a different status. That is a reopening path, and CLAUDE.md forbids it: a `hold` or a
`no-go` halts the pipeline. Four pins in `tests/test_quality.py::TestGateClosuresAreScored`
hold the line — closure is scored, closure is never verified, closure is never retried, and
an ordinary agent's `blocked` is still *not* scored, since there it does mean unused work.

Cost: one grading call (~$0.09) per gate closure, no verdict call. A halted run remains
cheaper than an accepted one.

**Still open, and not the same question:** whether the rubric *discriminates*. The re-run
scored 3/3 again — genuinely earned on that case, since it caught the preprint
mislabelling, the completers-only sample, the self-report measure, and the disclaimed
causation. But every fact-checker score on record is still a 3. The censoring is fixed; the
absence of observed variance is not, and a baseline with no spread still cannot prove a
cheaper model is worse. → the 6b entry above.

**Original finding, for the record:**

`orchestrator.py:261` scores only on `Verdict.ACCEPT`. `blocked` short-circuits before a
verdict is even requested, so it is never scored. For an ordinary agent that is right —
`blocked` there means a gate was hit or a prerequisite was missing, and the work is not
being used. For a **gate** agent, `blocked` is the deliverable: it is how the gate returns
closed. The result is that `qa`, `fact-checker`, `risk-review`, and `legal-review` can only
be scored on inputs they did not need to stop.

Evidence: of 8 `fact-checker` delegations, 3 returned `blocked` and were never scored, 2
were `partial`-then-`revise`d to failure and never scored, and the only 3 that scored were
the deliberately easy set — which scored 3.0/3 on every dimension with zero variance.

Fix direction, not yet decided: `roster.py` already carries `is_gate`, so scoring a gate's
`blocked` return is available without new plumbing. The open questions are whether a gate
closure should be scored against the same rubric or a different one (the rubric currently
grades the analysis, which is present in a closure), and whether a closure needs a manager
verdict first — today it deliberately skips one, which is a real cost saving on a halted
run and would have to be traded off knowingly.

Do not fix this by writing easier gate tests. The censoring is structural.

### Config floor — `load()` can widen the guardrails it is supposed to enforce
`config.py:184-192` applies a `config.json` patch to `denied_tools`, `permission_mode`,
and `setting_sources` with no minimum. `{"delegation": {"permission_mode":
"bypassPermissions"}}` disables every runtime protection while `allowed_tools` still
reads correctly, and `mastery check` would still print OK. Not reachable by a sub-agent —
none has a write tool — so this is a floor, not a hole. Fix: refuse in `load()` to remove
any default-denied tool, to widen `permission_mode` past `dontAsk`, or to add a setting
source, and fail loudly rather than clamping silently. Raised 2026-07-31; see APPENDIX.

### Egress review — read-only is not no-exfiltration
`roster.py:84` grants researcher `WebSearch` + `WebFetch`, `roster.py:104` grants
fact-checker `WebFetch`. Both are required for those roles to function. The exposure is
prompt injection from fetched content inducing a request to an attacker-controlled URL
with brief context in the query string. Mitigated today by hand-assembled minimal context
and the 60 KB cap. Worth deciding explicitly whether that is accepted or whether fetches
need a domain allowlist. Raised 2026-07-31; see APPENDIX.

### Live gate test — DONE for all four gates 2026-07-31
`qa` closed the set (`briefs/20260731-ff-001.json`): a synthetic FaithFeed 2.14.0 release
candidate with three planted problems, a hard 09:00 promotion deadline, and a booked
marketing chain. Same mechanics: `status=blocked`, **1 attempt, no retry**, **0 verdict
calls**, **0 quality scores**, `gate_hit`, returned to operator. $0.32, 2 turns, 161s
(run log `89cff7b32330`). **Four-gate total: $1.05.**

**It caught 2 of the 3 planted problems, and this is recorded as 2 of 3, not as a pass.**

Caught:
- The share-link blocker — access controlled solely by base36 primary key, dev note "the id
  space is large enough that guessing is impractical". Rated **blocker** on data exposure,
  and it named the sharper failure the design hid: possession of a leaked link grants
  standing access regardless of guessability.
- The auth-refresh regression — it read the dev's own "much smoother UX, no more surprise
  logouts" note and identified that the 401-triggered recovery path had been *removed and
  not replaced*, leaving a silently-stale session until the next tick.

**Missed:** the offline-indicator item, planted specifically to test *"severity is based on
user impact, not effort to fix"*. The dev note called it "purely cosmetic, deferred to
2.15"; the actual impact is a user shown yesterday's devotional believing it is today's.
`qa` accepted the framing — the words "indicator" and "cosmetic" appear nowhere in its
return. It treated offline only as a coverage gap, never as a defect whose severity label
was wrong. That is precisely the rule most likely to matter in production, and it did not
fire.

Beyond the plants, unprompted: it refused to count mobile-dev's single-device self-report
as coverage; produced a long not-tested list with a reason per item; noticed that FF-287's
underlying file `PrayerListRepository.kt` was modified by this release and flagged the
untested regression risk; identified both applicable escalation cases; **held the no-go
explicitly against the deadline** ("deadline pressure does not change this verdict"); and
applied *"do not approve a release you could not exercise"* to itself, labelling its own
findings design-level pending hands-on confirmation.

---
**Superseded entry (three gates), for the record:**
`legal-review` was run on the handoff `risk-review` actually produced, not on a fresh
invention: its brief (`briefs/20260731-rd-003.json`) quotes risk-review's three escalated
questions verbatim and scopes the task to them. Same mechanics: `status=blocked`, **1
attempt, no retry**, **0 verdict calls**, **0 quality scores**, `gate_hit`, returned to
operator. $0.18, 2 turns, 71s (run log `267c760ab73d`).

It held every constraint its doc imposes: stated the not-legal-advice disclaimer and the
absence of an attorney relationship; refused to determine truth/falsity, statutory
applicability, or predict outcomes; produced three counsel-required questions specific
enough to hand to a lawyer; stated explicitly that absence of a flag is not clearance and
bounded what it had reviewed; and declined to repeat risk-review's seven flags.

It also self-identified a coverage gap nobody briefed it to look for: **minors'-data legal
exposure has been assessed by no one.** risk-review covered the policy dimension, and this
task's scope was the three handoff items, so the legal dimension of an ungated
minors-reachable surface fell between them. Worth deciding whether the mandatory pipeline
should route that explicitly.

**Three-gate chain total: $0.73.** The whole Research-and-Debunk gate surface, proven live,
for less than a dollar.

---
**Superseded entry (two gates), for the record:**
`risk-review` exercised the same way (`briefs/20260731-rd-002.json`): a draft that is
factually defensible, so it cannot be stopped on facts, but carrying doxxing of a named
private individual, an implied threat, non-consensual private screenshots, a direct
medication-discontinuation instruction, and engagement bait, on an ungated surface where
minors are reachable. Identical mechanics: `status=blocked`, **1 attempt, no retry**, **0
verdict calls**, **0 quality scores**, `gate_hit` logged, returned to operator. $0.30,
4 turns, 90s (run log `6f374a53ffa1`).

It raised 7 flags with exact excerpts and concrete replacements, listed the categories it
checked and found clean, and — the part worth noting — **honoured its own boundary**: it
named the defamation, harassment-statute, and privacy-tort questions and handed them to
`legal-review` rather than answering them, exactly as its escalation cases require.

**That handoff has nowhere to go.** `legal-review` is a gate, is unrubriced, and therefore
cannot run. So the escalation path this test just exercised terminates at an agent that
`RubricMissing` would halt before any spend. → BACKLOG below.

---
**Original entry, for the record:**
Run logs contained delegations for `researcher` and `content` only. Fixed for one of the
two gates by briefing a draft with six planted defects (`briefs/20260731-rd-001.json`) and
verifying the halt mechanically rather than by reading the prose:

| Assertion | Result |
|---|---|
| Returned `status` | `blocked` — the doc's *not publishable* → `blocked` mapping holds end to end |
| Delegation attempts | 1. **No retry** — `blocked` is not retried the way `failed` is |
| Manager verdict call | none — `blocked` short-circuits before verification, so a halted run does not pay for a verdict |
| `quality_score` events | 0 — correctly unscored; `blocked` is not an accepted outcome |
| Cost | $0.26, 2 turns, 102s (run log `37b3b3f3ceae`) |

The agent caught all six planted defects and two more that were not deliberate.

**Two findings the test surfaced, both pre-spend halts working as designed:**

1. **`fact-checker` could not run at all.** `RubricMissing` halted the run before any
   delegation — an accepted output cannot be left unscored, and it had no rubric. That is
   *why* the gate had never been exercised; not neglect, a structural block. A rubric was
   added (5 dimensions, all derived from the agent's own "Rules and guardrails" rather than
   invented) and `tests/test_quality.py`'s hardcoded pin updated deliberately, as it is
   designed to force. **`risk-review` is still unrubriced and still cannot run** — that is
   the remaining half of this item.
2. **`approval_gates_touched` is a token, not commentary.** The first attempt declared it
   in prose ("none for this task itself, but the draft is destined for public output…"),
   which `gates.check` classified as `unrecognized` and halted on. Correct fail-closed
   behaviour — an unrecognized declaration is not a clearance — but worth knowing when
   writing briefs by hand: the field takes `none` or a name from `GATE_NAMES`, and nuance
   belongs in `constraints`.

### Agent coverage — 11 of 17 delegatable agents have never run
Measured from `.runs/` on 2026-07-31, not from recollection. **Nothing is blocked any
more**: rubric coverage is complete, so every remaining gap is unexercised rather than
unrunnable. That is a real change in kind — the previous entry listed ten agents that
`RubricMissing` would have halted before they spent anything.

| | Agents |
|---|---|
| **Ever run (6)** | `researcher` (7), `content` (3), `fact-checker` (1), `risk-review` (1), `legal-review` (1), `qa` (1) |
| **Runnable, never run (11)** | `mobile-dev`, `ops`, `strategy`, `marketing`, `ui-ux`, `data-model-agent`, `metrics-agent`, `incident-response-agent`, `prompt-engineer-agent`, `user-research-agent`, `competitor-intelligence-agent` |

All four gates are in the first row. The eleven remaining are ordinary agents: a gap in
each is a gap in capability, not a hole through which something ships unreviewed.

Two of these matter more than the rest, both gates:

- ~~`legal-review`~~ — **done 2026-07-31.** Rubriced and exercised on the real handoff.
- ~~`qa`~~ — **done 2026-07-31 (mechanics).** See the gate-test entry above. **All four
  gates now proven live.** The second qa test — whether it is actually good at QA against
  real FaithFeed material rather than a synthetic candidate — remains open and does require
  an actual app change. Test 1 isolated the wiring from the judgment, so a disappointment in
  test 2 will be unambiguously the agent and not the plumbing.

Writing a rubric is not clerical — it defines what "good" means for a role and feeds the
eval baselines. Each should be derived from that agent's own doc, as the `fact-checker`,
`risk-review`, and `legal-review` ones were, and each will break the hardcoded pin in
`test_quality.py` by design.

**Rubric coverage is complete as of 2026-07-31 — all 17 delegatable agents.** No agent is
now blocked from running by `RubricMissing`. Review status differs, and the difference is
the point:

| | Agents | Status |
|---|---|---|
| Pre-existing | `researcher`, `content`, `mobile-dev`, `qa`, `data-model-agent` | shipped with Stop 7 |
| **Operator-reviewed 2026-07-31** | `fact-checker`, `risk-review`, `legal-review` | drafted from each agent's doc, reviewed and **passed** by the operator |
| **Not yet reviewed** | `marketing`, `ops`, `strategy`, `ui-ux`, `metrics-agent`, `incident-response-agent`, `prompt-engineer-agent`, `user-research-agent`, `competitor-intelligence-agent` | drafted 2026-07-31 from each agent's own "Rules and guardrails"; **no human has checked them** |

That last row will produce scores the moment those agents run, and those scores will anchor
a trend, whether or not anyone has agreed the criteria are right. That is the
"looks like a measurement" failure this ledger exists to catch, so it is stated rather than
left to be discovered from a graph later.

**A pin lost its subject when the set completed.** `test_unrubriced_agent_halts_before_any_spend`
named `strategy` as its unrubriced example. `strategy` now has a rubric, so the test stopped
testing anything — it surfaced only because the scripted runner refused a call it should
never have received. Repaired by patching the rubric table to empty and asserting the
behaviour, rather than depending on some roster agent staying uncovered. A pin that relies
on another part of the system remaining incomplete is not a pin. The companion test was
inverted at the same time: it now asserts that **every** delegatable agent is rubriced, so
removing a rubric — or adding an agent without one — breaks the build.

### Governor layer names one vertical's roles and release vocabulary
`pipelines.py:71-75` hardcodes `RELEASE = ("mobile-dev", "qa", OPERATOR_APPROVAL,
"promote to track")`. Two separate leaks in one definition: the agent names, and
**"promote to track", which is Google Play vocabulary**. `PUBLIC_OUTPUT` has the same
shape and is only less conspicuous because `content`/`fact-checker`/`risk-review` read
as generic roles rather than one vertical's org chart.

Contradicts the north star directly: if agents are the commodity, the governor must not
name any specific one.

Shape of the fix — parameterise pipelines by **stage kind**, with the vertical supplying
the concrete agents:

    build -> verify -> approve -> promote

- The governor defines the kinds and the ordering. It names no agent.
- A vertical maps kinds to its own agents (FaithFeed: build=`mobile-dev`, verify=`qa`).
- **The terminal stage must be generic too** — `promote` or `release` as the kind, with
  the channel noun ("track", "store listing", "feed") supplied by the vertical.
  Parameterising the agent names while leaving "promote to track" in place is a half-fix
  that reads as done: the governor would still carry one distribution channel's
  fingerprint.

Why this dissolves two problems at once:
1. The governor stops naming specific agents.
2. The pipeline guardrail test — "a `qa` no-go halts the release pipeline" — becomes a
   test of the *halting property*, expressible with any two rubriced agents. It no longer
   needs FaithFeed's agents to exist, which is what forced tonight's rubric expansion.

**Do not delete the `mobile-dev` and `qa` rubrics when this lands.** They were written
tonight (Stop 7) to keep a governor guardrail test writable under fail-closed, and they
look like test scaffolding but are not. Once stage kinds exist, they are *vertical*
rubrics and belong in the vertical's config, on the correct side of the line. They move;
they are not discarded.

Deserves its own stop — it is a real refactor of enforcement code, not a cleanup.

### Stop 7 baseline briefs are vertical-adjacent
`briefs/20260729-rd-005.json`, `-006`, `-007` are Instagram Graph API subject matter used
as a governor-track measurement. The grades are valid and the runs are done — subject
matter does not affect whether a rubric dimension was correctly scored. Flagged for
provenance only. **Next fresh-baseline briefs should be vertical-neutral.**

Deliberately not corrected retroactively: re-running fresh briefs to launder provenance
would cost real spend for a purity gain that this note achieves for free.

### Smaller items
- Cap CONTEXT/history in brief with rolling summary
- Bound `deliverables[]` item length
- Fix filename typo `task_breif_template.md` (only if a path references it)
- `gates.check()` returns only the first matching gate; consider returning all of them
- No retention or purge path in `runlog.py` — logs hold operator prose and returned work indefinitely
- `pyproject.toml` `packages.find` excludes `integrations/`, so `from integrations.meta_client import ...` breaks outside repo-root cwd — a portability gap against the VPS/mobile-shell requirement
- `pipelines.needs_legal_review` is dead code, called nowhere; either wire it into `run_pipeline` or delete it. `drafter.py:250` prints a legal-review line that reads like enforcement but is not.
