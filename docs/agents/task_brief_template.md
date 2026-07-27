# task_brief_template

The delegation contract, manager → sub-agent. One brief, one agent, one task.
Every section is filled before the brief is sent. No blank sections, no `TBD`.
Where a section genuinely does not apply, write `none` — the explicit word, not an empty line.

An unfilled brief is not sent. If a section cannot be filled because the operator did not
supply it, that is an escalation, not a gap to guess at.

---

## Template

```markdown
# Task Brief

**task_id:** YYYYMMDD-<ff|rd|ops>-NNN
**agent:** <exactly one agent from docs/agents/README.md>
**vertical:** <FaithFeed | Research and Debunk | Operations and Sourcing>
**urgency:** <none | date the work is needed by, and what depends on it>

## Objective
<One sentence. What this task produces. Not why it matters, not the background.>

## Success criteria
<Checkable list. The agent's return is verified against exactly these.>
- <criterion>
- <criterion>

## Context provided
<Everything the agent receives, listed item by item. Nothing outside this list is passed.>
- docs/agents/<agent>.md
- <prior task_id and the accepted output it contributes>
- <file, excerpt, figure, or draft — named, not gestured at>

## Constraints
<Fixed limits: files that may be touched, length caps, channel, platform, tone, budget.>

## Out of scope
<What this agent must not do on this task, especially where an adjacent agent owns it.>

## Approval gates touched
<none | the specific gate: money, production, permissions, public output, destructive.>

## Expected deliverables
<The labels expected in the return's `deliverables` array. Per the agent's own doc.>
- <label>
- <label>
```

---

## Filling rules

**task_id** — `YYYYMMDD-<vertical>-<nnn>`, verticals `ff`, `rd`, `ops`. Example
`20260727-ff-014`. Assigned by the manager, echoed back verbatim in the return.

**agent** — Exactly one. Two agents means two briefs, sequenced. Chosen by applying
`manager_decision_rubric.md`, not by intuition.

**Objective** — One sentence. If it needs two, it is two tasks.

**Success criteria** — Written so the manager can verify the return without re-doing the work.
"Good copy" is not a criterion. "Three variants, each under 280 characters, each with a
distinct angle" is.

**Context provided** — This is the whole payload. Context is opt-in and assembled by hand.
Never pass `CLAUDE.md`, chat history, or unrelated project docs. The agent's own doc from
`docs/agents/` **must** be listed here — agent docs are not auto-loaded for delegated
sub-agents, so omitting it leaves the agent with no role definition.

**Constraints** — State the limits that would otherwise be discovered by violating them.

**Out of scope** — Pull directly from the "Does not own" column in
`docs/agents/README.md` and the agent's "What it must not do" section.

**Approval gates touched** — If any gate is named here, the orchestrator halts before the
work is delegated, not after it returns.

**Expected deliverables** — Mirrors the "Outputs it should produce" section of the agent's
doc. Sets the labels the return is checked against.

---

## Worked example

```markdown
# Task Brief

**task_id:** 20260727-ff-014
**agent:** mobile-dev
**vertical:** FaithFeed
**urgency:** none

## Objective
Fix the crash on pull-to-refresh when the feed is empty.

## Success criteria
- Cold start with no cached posts, then pull to refresh, does not crash.
- Empty state renders instead.
- Manual test steps supplied for qa.

## Context provided
- docs/agents/mobile-dev.md
- FeedViewModel.kt, current contents
- Crash report: IndexOutOfBounds at FeedViewModel:118, 41 occurrences, app 2.4.1
- Repro: cold start, no cache, pull to refresh
- versionName 2.4.1, versionCode 241, minSdk 26, targetSdk 35
- Release track: internal

## Constraints
- Touch FeedViewModel.kt only.
- No new dependencies.
- No version bump on this task.

## Out of scope
- Do not test or sign off — qa owns that.
- Do not redesign the empty state — ui-ux owns that.
- Do not promote to any track.

## Approval gates touched
none

## Expected deliverables
- FeedViewModel.kt
- change rationale
- manual test steps
```
