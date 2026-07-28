# mastery-ai

Personal agent operating system. Code-owned, guardrail-driven, multi-agent.
The orchestrator routes work, assembles context by hand, enforces the caps and
gates, and verifies every return before the pipeline continues.

Design and constraints: [CLAUDE.md](CLAUDE.md). Per-agent detail: [`docs/agents/`](docs/agents/).

## Output

Finished work, newest first. These are the pages worth opening from a phone.

| What | Status |
|---|---|
| [HJR-192 debunk — content drafts](docs/content/20260728-hjr192-drafts.md) | Accepted. **Not cleared for publication** — fact-checker, risk-review, and legal-review still stand between these and a post. |
| [HJR-192 — evidence base](docs/research/20260728-rd-001-hjr192.md) | Refused by the verdict on sourcing provenance; admitted by operator override, recorded in the file. |
| [Promoter liability — addendum](docs/research/20260728-rd-002-promoter-liability.md) | Accepted. 26 U.S.C. § 6700, § 7402, and *United States v. Kirk*. |

Nothing here publishes itself. Publishing is manual and stays the operator's.

## Running it

```sh
mastery check                    # validate config, roster, and schemas — no model call
mastery draft <request>          # propose briefs from a raw request; runs nothing
mastery run <brief.json>         # run one brief to a verified outcome
mastery verify <brief.json>      # verify a delegation already in the run log
```

`draft` writes each stage's context as `<<< FILL >>>` placeholders and stops.
Filling them is the operator's step, and it is what keeps context opt-in rather
than assembled on a model's say-so.

The delegation cap is per operator request, and one `mastery run` is one request.
A plan whose stage count reaches the cap runs as separate invocations, not as a
single pipeline.

### From a VPS or a phone shell

```sh
git clone https://github.com/LMW-Labs/mastery-ai.git && cd mastery-ai
pip install -e .
mastery check
```

Auth is the Claude Code OAuth credential (`~/.claude/.credentials.json`), so the
box needs Claude Code signed in. `auth.mode="subscription"` asserts no
`ANTHROPIC_API_KEY` is set — a key would shadow OAuth and bill the API account
instead, which is the silent billable fallback CLAUDE.md forbids.

Output is plain text, no TUI, no interactive prompts. `stdout` is forced to
UTF-8 so a legacy console codepage cannot destroy a finished report.

## Run logs

One JSONL per operator request in `.runs/`, **gitignored** — logs are local to
the machine that produced them and do not travel with this repo. They carry the
full audit trail: every delegation, its cost and turn count, the manager verdict
and its reasoning, permission denials, and the returned deliverables.

That last one matters. A delegation that returns work and then fails downstream
still has its output on disk, and `mastery verify` can finish the cheap half
rather than paying for the research twice.

## Tests

```sh
python -m unittest discover -s tests -t .
```

98 tests, no SDK, no network, no credential. The guardrails are this package's
own code, so they are provable without a model — swap `Runner` for a fake and
the whole orchestrator runs offline.
