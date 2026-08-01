-- Mastery OS run-log projection.
--
-- This schema is a *mirror* of the JSONL run logs, not a replacement for them.
-- runlog.py stays the source of truth: it is a local append with no network
-- dependency, which is the only reason a run that dies mid-flight still leaves
-- a record. Putting a socket in that path would create the exact failure mode
-- runlog.py's docstring exists to prevent -- a run that dies AND leaves silence.
--
-- Consequences of that choice, made deliberately:
--   * `events` stores each record verbatim as jsonb. Nothing is dropped on the
--     way in, so a field added to runlog.py lands here without a migration and
--     without being silently discarded.
--   * The typed shapes below are VIEWS, not tables. There is no second write
--     path, so the projection cannot drift from what was logged.
--   * Ingest is idempotent on (run_id, seq). Re-running it over the same logs
--     inserts nothing, so it is safe on a cron or after a partial failure.
--
-- Applied by scripts/provision_postgres.sh. Safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS events (
    run_id      text    NOT NULL,
    seq         integer NOT NULL,          -- 0-based line number within the run's JSONL
    ts          timestamptz,               -- NULL only if a record predates the ts field
    event       text    NOT NULL,
    task_id     text,                      -- lifted out of payload; NULL for run-level events
    payload     jsonb   NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, seq)
);

COMMENT ON TABLE events IS
    'Verbatim mirror of .runs/<run_id>.jsonl. One row per logged record. '
    'Append-only; the ingester never updates or deletes.';
COMMENT ON COLUMN events.seq IS
    'Line number within the run log. With run_id it makes re-ingest a no-op.';

CREATE INDEX IF NOT EXISTS events_event_idx   ON events (event);
CREATE INDEX IF NOT EXISTS events_task_id_idx ON events (task_id) WHERE task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_ts_idx      ON events (ts DESC);
CREATE INDEX IF NOT EXISTS events_payload_idx ON events USING gin (payload);

-- -- typed projections ------------------------------------------------------
-- Every view reads only from `events`. Adding one costs nothing at write time.

CREATE OR REPLACE VIEW v_runs AS
SELECT
    s.run_id,
    s.ts                                AS started_at,
    e.ts                                AS ended_at,
    EXTRACT(EPOCH FROM (e.ts - s.ts))   AS wall_seconds,
    s.payload ->> 'request'             AS request,
    e.payload ->> 'outcome'             AS outcome,
    e.payload ->> 'detail'              AS detail
FROM      events s
LEFT JOIN events e ON e.run_id = s.run_id AND e.event = 'run_end'
WHERE s.event = 'run_start';

COMMENT ON VIEW v_runs IS
    'One row per operator request. ended_at NULL means the run died before '
    'run_end -- a real outcome, not missing data.';

CREATE OR REPLACE VIEW v_delegations AS
SELECT
    e.run_id,
    e.task_id,
    e.ts                                                AS ended_at,
    e.payload ->> 'agent'                               AS agent,
    e.payload ->> 'status'                              AS status,
    e.payload ->> 'role_tier'                           AS role_tier,
    e.payload ->> 'model'                               AS model,
    (e.payload ->> 'duration_s')::numeric               AS duration_s,
    (e.payload ->> 'num_turns')::integer                AS num_turns,
    (e.payload ->> 'cost_usd')::numeric                 AS cost_usd,
    (e.payload ->> 'input_tokens')::bigint              AS input_tokens,
    (e.payload ->> 'output_tokens')::bigint             AS output_tokens,
    (e.payload ->> 'cache_read_tokens')::bigint         AS cache_read_tokens,
    (e.payload ->> 'cache_creation_tokens')::bigint     AS cache_creation_tokens,
    (s.payload ->> 'context_bytes')::integer            AS context_bytes,
    (s.payload ->> 'attempt')::integer                  AS attempt,
    s.payload -> 'tool_tier'                            AS tools_granted,
    e.payload -> 'permission_denials'                   AS permission_denials,
    jsonb_array_length(
        COALESCE(e.payload -> 'permission_denials', '[]'::jsonb))
                                                        AS denial_count,
    e.payload ->> 'summary'                             AS summary,
    e.payload -> 'deliverables'                         AS deliverables,
    e.payload -> 'risks'                                AS risks,
    e.payload ->> 'next_step'                           AS next_step
FROM      events e
LEFT JOIN events s
       ON s.run_id  = e.run_id
      AND s.event   = 'delegation_start'
      AND s.task_id = e.task_id
      AND s.seq     < e.seq
WHERE e.event = 'delegation_end';

COMMENT ON VIEW v_delegations IS
    'Completed delegations, joined back to their delegation_start for the '
    'granted tool list and context size. A start with no end (timeout, crash) '
    'does not appear here -- see v_open_delegations.';

CREATE OR REPLACE VIEW v_open_delegations AS
SELECT
    s.run_id,
    s.task_id,
    s.ts                                     AS started_at,
    s.payload ->> 'agent'                    AS agent,
    (s.payload ->> 'attempt')::integer       AS attempt,
    (s.payload ->> 'context_bytes')::integer AS context_bytes
FROM events s
WHERE s.event = 'delegation_start'
  AND NOT EXISTS (
      SELECT 1 FROM events e
      WHERE e.run_id  = s.run_id
        AND e.event   = 'delegation_end'
        AND e.task_id = s.task_id
        AND e.seq     > s.seq
  );

COMMENT ON VIEW v_open_delegations IS
    'Delegations that started and never ended. This is the timeout/crash '
    'signal runlog.py is built to surface; it should normally be empty.';

CREATE OR REPLACE VIEW v_verdicts AS
SELECT
    run_id,
    task_id,
    ts                                              AS decided_at,
    payload ->> 'verdict'                           AS verdict,
    payload ->> 'reason'                            AS reason,
    payload ->> 'role_tier'                         AS role_tier,
    payload ->> 'model'                             AS model,
    (payload ->> 'duration_s')::numeric             AS duration_s,
    (payload ->> 'num_turns')::integer              AS num_turns,
    (payload ->> 'cost_usd')::numeric               AS cost_usd,
    (payload ->> 'input_tokens')::bigint            AS input_tokens,
    (payload ->> 'output_tokens')::bigint           AS output_tokens,
    (payload ->> 'cache_read_tokens')::bigint       AS cache_read_tokens,
    (payload ->> 'cache_creation_tokens')::bigint   AS cache_creation_tokens
FROM events
WHERE event = 'verdict';

CREATE OR REPLACE VIEW v_quality AS
SELECT
    run_id,
    task_id,
    ts                                              AS scored_at,
    payload ->> 'agent'                             AS agent,
    payload ->> 'rubric_version'                    AS rubric_version,
    (payload ->> 'overall')::numeric                AS overall,
    (payload ->> 'normalised')::numeric             AS normalised,
    payload -> 'dimension_scores'                   AS dimension_scores,
    payload ->> 'role_tier'                         AS role_tier,
    payload ->> 'model'                             AS model,
    (payload ->> 'duration_s')::numeric             AS duration_s,
    (payload ->> 'cost_usd')::numeric               AS cost_usd
FROM events
WHERE event = 'quality_score';

CREATE OR REPLACE VIEW v_quality_skipped AS
SELECT
    run_id,
    task_id,
    ts                      AS skipped_at,
    payload ->> 'agent'     AS agent,
    payload ->> 'reason'    AS reason
FROM events
WHERE event = 'quality_skipped';

CREATE OR REPLACE VIEW v_gate_hits AS
SELECT
    run_id, task_id,
    ts                      AS hit_at,
    payload ->> 'gate'      AS gate,
    payload ->> 'detail'    AS detail
FROM events
WHERE event = 'gate_hit';

CREATE OR REPLACE VIEW v_failures AS
SELECT
    run_id, task_id,
    ts                      AS failed_at,
    payload ->> 'kind'      AS kind,
    payload ->> 'detail'    AS detail
FROM events
WHERE event = 'failure';

-- A stage's true cost: its delegation plus every verdict and grade on the same
-- task_id. runlog.py names this join explicitly ("a stage's true cost is its
-- delegation_end plus every verdict sharing that id"); encoding it here means
-- nobody has to remember to add the verdict cost by hand and under-report.
CREATE OR REPLACE VIEW v_stage_cost AS
SELECT
    d.run_id,
    d.task_id,
    d.agent,
    d.status,
    d.role_tier,
    d.cost_usd                                  AS delegation_cost_usd,
    COALESCE(vd.verdict_cost_usd, 0)            AS verdict_cost_usd,
    COALESCE(q.quality_cost_usd, 0)             AS quality_cost_usd,
    COALESCE(d.cost_usd, 0)
      + COALESCE(vd.verdict_cost_usd, 0)
      + COALESCE(q.quality_cost_usd, 0)         AS total_cost_usd,
    vd.verdicts,
    vd.last_verdict,
    q.overall                                   AS quality_overall,
    q.normalised                                AS quality_normalised
FROM v_delegations d
LEFT JOIN (
    SELECT run_id, task_id,
           SUM(COALESCE(cost_usd, 0))                       AS verdict_cost_usd,
           COUNT(*)                                         AS verdicts,
           (ARRAY_AGG(verdict ORDER BY decided_at DESC))[1] AS last_verdict
    FROM v_verdicts GROUP BY run_id, task_id
) vd ON vd.run_id = d.run_id AND vd.task_id = d.task_id
LEFT JOIN (
    SELECT run_id, task_id,
           SUM(COALESCE(cost_usd, 0)) AS quality_cost_usd,
           AVG(overall)               AS overall,
           AVG(normalised)            AS normalised
    FROM v_quality GROUP BY run_id, task_id
) q ON q.run_id = d.run_id AND q.task_id = d.task_id;

COMMENT ON VIEW v_stage_cost IS
    'Full cost and outcome of one stage: delegation + verdicts + grading. '
    'Use this rather than v_delegations.cost_usd alone, which omits the '
    'manager and grader calls made on the same budget.';

COMMIT;
