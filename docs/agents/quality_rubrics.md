{
  "_note": [
    "Per-role quality rubrics. Loaded by mastery/quality.py — this file is the",
    "one definition, not a copy that drifts, same arrangement as",
    "structured_output_schema.md.",
    "",
    "Scored 0-3 against the anchored descriptors below. Anchors exist so a score",
    "means the same thing in March and in July: a bare number with no level",
    "definition drifts with whoever is grading, and a trend built on drifting",
    "numbers measures the grader, not the work.",
    "",
    "These dimensions are deliberately NOT 'were the success criteria met'. That",
    "question is the manager verdict's, it is schema-bound, and it is control",
    "flow. These are gradations *within* met — met-thinly versus met-well — so",
    "the two calls are not paying twice for one answer.",
    "",
    "rubric_version is bumped on any change to a dimension or an anchor. Scores",
    "from different versions are not comparable and `mastery eval` refuses to",
    "group them together.",
    "",
    "An agent absent from this file cannot be scored, and an accepted outcome for",
    "an unrubriced agent raises RubricMissing rather than silently skipping —",
    "silent skipping is the bypass the STOP 7 pin exists to catch."
  ],
  "researcher": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "source_primacy",
        "asks": "Are claims carried by primary sources rather than commentary about them?",
        "anchors": {
          "0": "No sources, or only aggregators and commentary.",
          "1": "Mixed, with primary sources named but not actually relied on.",
          "2": "Mostly primary; secondary used only where no primary exists.",
          "3": "Primary throughout, and where only secondary exists that is stated as such."
        }
      },
      {
        "dimension": "citation_traceability",
        "asks": "Can a reader reach each source and find the specific passage relied on?",
        "anchors": {
          "0": "Claims with no citation, or citations too vague to follow.",
          "1": "Sources named but not locatable — no URL, section, or identifier.",
          "2": "Every source locatable; the specific passage sometimes left to the reader.",
          "3": "Every claim traceable to a locatable source and a specific passage within it."
        }
      },
      {
        "dimension": "question_coverage",
        "asks": "Was the question actually answered, including its inconvenient parts?",
        "anchors": {
          "0": "Answers a different, easier question.",
          "1": "Answers the easy part; the hard part is unaddressed and unmentioned.",
          "2": "Covers the question; a gap or two named in risks.",
          "3": "Covers the question, and where evidence was unavailable that is stated plainly."
        }
      },
      {
        "dimension": "evidence_inference_separation",
        "asks": "Is what a source says kept distinct from what the agent concluded?",
        "anchors": {
          "0": "Inference presented as if it were sourced.",
          "1": "Blurred; a reader cannot reliably tell which is which.",
          "2": "Mostly separated, with occasional slippage.",
          "3": "Consistently separated — sourced claims and the agent's reading are distinguishable throughout."
        }
      }
    ]
  },
  "content": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "executes_the_given_angle",
        "asks": "Does the copy execute the angle it was handed, rather than substituting its own?",
        "anchors": {
          "0": "Different angle entirely.",
          "1": "Drifts off the angle partway through.",
          "2": "On the angle, somewhat generically.",
          "3": "Executes the given angle specifically, and would not fit a different one."
        }
      },
      {
        "dimension": "hook_strength",
        "asks": "Does the opening earn the next line without overclaiming?",
        "anchors": {
          "0": "No hook, or a hook that misrepresents what follows.",
          "1": "Generic opener that would fit any post on any topic.",
          "2": "Specific and readable; not especially compelling.",
          "3": "Specific, compelling, and honest about what the piece delivers."
        }
      },
      {
        "dimension": "cta_present_and_matched",
        "asks": "Is there a call to action, and does it match what the piece actually supports?",
        "anchors": {
          "0": "No CTA.",
          "1": "CTA present but disconnected from the content.",
          "2": "CTA present and relevant.",
          "3": "CTA present, relevant, and proportionate to the strength of the evidence given."
        }
      },
      {
        "dimension": "declared_constraints_honored",
        "asks": "Were the brief's stated constraints — length, count, platform, forbidden phrasings — met exactly?",
        "anchors": {
          "0": "Constraints ignored.",
          "1": "One or more constraints missed without acknowledgement.",
          "2": "All constraints met.",
          "3": "All constraints met, and any tension between a constraint and the objective is named rather than silently resolved."
        }
      }
    ]
  },
  "_scope_note": [
    "Five rubrics, not the three originally scoped. researcher, content, and",
    "data-model-agent were the approved set. mobile-dev and qa are added because",
    "the RELEASE pipeline is mobile-dev -> qa by definition (pipelines.py), so",
    "without rubrics for both, fail-closed makes that pipeline unrunnable and",
    "its guardrail tests unwritable. Flagged rather than assumed silently.",
    "",
    "The remaining twelve agents are deliberately absent and will fail closed."
  ],
  "mobile-dev": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "scope_discipline",
        "asks": "Did the change stay inside the files and behaviour the brief named?",
        "anchors": {
          "0": "Touched unrelated code or made design decisions it does not own.",
          "1": "Stayed roughly in scope, with incidental unrelated edits.",
          "2": "In scope.",
          "3": "In scope, and where a fix required touching something else that is named rather than done quietly."
        }
      },
      {
        "dimension": "root_cause_not_symptom",
        "asks": "Does the change address the cause, or suppress the visible effect?",
        "anchors": {
          "0": "Suppresses the symptom — a caught-and-ignored error, a guard around the crash.",
          "1": "Partial fix that leaves the underlying condition reachable.",
          "2": "Addresses the cause.",
          "3": "Addresses the cause, and says what the cause was in terms a reviewer can check."
        }
      },
      {
        "dimension": "verifiability",
        "asks": "Can someone else confirm this works without redoing the investigation?",
        "anchors": {
          "0": "No way to tell whether it works.",
          "1": "Claims it works with nothing to check against.",
          "2": "Names how to verify.",
          "3": "Names how to verify, including the failing case that previously reproduced."
        }
      }
    ]
  },
  "qa": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "regression_coverage",
        "asks": "Were the paths the change could have broken actually exercised?",
        "anchors": {
          "0": "Only the happy path.",
          "1": "Happy path plus one obvious variant.",
          "2": "The affected paths covered.",
          "3": "Affected paths plus the adjacent ones the change could plausibly reach."
        }
      },
      {
        "dimension": "edge_cases_named",
        "asks": "Are the boundaries stated concretely — empty, offline, first-run, permission-denied?",
        "anchors": {
          "0": "No edge cases considered.",
          "1": "Edge cases mentioned generically.",
          "2": "Specific edge cases named and checked.",
          "3": "Specific edge cases named and checked, and any left unchecked stated as unchecked."
        }
      },
      {
        "dimension": "finding_reproducibility",
        "asks": "Can each finding be reproduced from what is written?",
        "anchors": {
          "0": "Findings asserted with no steps.",
          "1": "Vague steps that would need guesswork.",
          "2": "Reproducible steps for each finding.",
          "3": "Reproducible steps, expected versus actual, for each finding."
        }
      },
      {
        "dimension": "verdict_matches_evidence",
        "asks": "Does go/no-go follow from what was actually found, without deadline softening?",
        "anchors": {
          "0": "Verdict contradicts the findings.",
          "1": "Verdict hedged so it commits to nothing.",
          "2": "Verdict follows from the findings.",
          "3": "Verdict follows from the findings and names what would change it."
        }
      }
    ]
  },
  "data-model-agent": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "file_line_traceability",
        "asks": "Is every asserted field traced to a named file and line, rather than to general knowledge?",
        "anchors": {
          "0": "Assertions from general knowledge of the API, untraced.",
          "1": "Files named, lines absent, so claims cannot be checked cheaply.",
          "2": "Most assertions carry file and line.",
          "3": "Every assertion carries file and line; nothing is asserted from outside the code."
        }
      },
      {
        "dimension": "gaps_stated_not_filled",
        "asks": "Where the code does not answer a question, is that said — or is the gap filled by assumption?",
        "anchors": {
          "0": "Gaps filled with plausible invention, presented as findings.",
          "1": "Gaps filled, with a hedge somewhere in the prose.",
          "2": "Gaps mostly named as gaps.",
          "3": "Every gap named explicitly, including the words 'none exists' where nothing exists."
        }
      },
      {
        "dimension": "no_over_disclosure",
        "asks": "Does it avoid inventorying things the code does not actually do?",
        "anchors": {
          "0": "Inventories collection that is not happening.",
          "1": "Includes speculative or hypothetical items alongside real ones.",
          "2": "Confined to what the code does.",
          "3": "Confined to what the code does, with an explicit non-collection list separating the two."
        }
      },
      {
        "dimension": "exhaustiveness_honesty",
        "asks": "Is the claim to completeness itself honest?",
        "anchors": {
          "0": "Implies a complete inventory without having checked.",
          "1": "Silent on whether the list is complete.",
          "2": "States what was searched.",
          "3": "States what was searched, and says plainly in risks where exhaustiveness could not be confirmed."
        }
      }
    ]
  }
}
