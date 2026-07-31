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

- [ ] BLOCKER: Stop 7 MET, with a quality baseline recorded on the strong model **before** any role is tiered down
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

## BACKLOG (log, do not action mid-stop)

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
