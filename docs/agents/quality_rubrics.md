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
  },
  "fact-checker": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "claim_extraction_completeness",
        "asks": "Was every checkable assertion found, including the implied ones?",
        "anchors": {
          "0": "Only the headline claim was adjudicated; most assertions untouched.",
          "1": "Explicit numeric claims found; implied and superlative claims missed.",
          "2": "Explicit claims found, plus some implied ones; a checkable assertion or two left out.",
          "3": "Every checkable assertion adjudicated, including implied claims, superlatives, and attributions."
        }
      },
      {
        "dimension": "rating_calibration",
        "asks": "Does each rating match what the source actually supports, without softening?",
        "anchors": {
          "0": "Ratings contradict the sources, or a false claim is rated supported.",
          "1": "A weaker version of the claim was checked, so overstatement passed as supported.",
          "2": "Ratings defensible; a partially-supported claim or two rated too generously.",
          "3": "Each rating is the one the source permits — the claim as written is checked, not a softer reading."
        }
      },
      {
        "dimension": "source_attribution_specificity",
        "asks": "Does each rating name the specific source text it was checked against?",
        "anchors": {
          "0": "Ratings asserted with no reference to any source.",
          "1": "Sources named in general; which passage settled which claim is left to the reader.",
          "2": "Most ratings tied to a named source; a few left unattributed.",
          "3": "Every rating names the source and the specific passage, and says so plainly where no supplied source addresses the claim."
        }
      },
      {
        "dimension": "unchecked_declared_not_passed",
        "asks": "Are claims that could not be checked listed as such, rather than quietly passed?",
        "anchors": {
          "0": "Unverifiable claims silently rated supported.",
          "1": "Some unchecked claims passed without comment.",
          "2": "Unchecked claims noted, but why they could not be checked is vague.",
          "3": "Every unchecked claim is listed with the reason it could not be checked from the supplied sources."
        }
      },
      {
        "dimension": "correction_supportedness",
        "asks": "Is the corrected wording itself supported, rather than a new unsourced claim?",
        "anchors": {
          "0": "No corrections offered, or corrections that invent a source.",
          "1": "Corrections offered but no more supported than what they replace.",
          "2": "Corrections mostly supported; one or two still reach past the source.",
          "3": "Every correction is wording the supplied source actually supports, and no citation is invented to close a gap."
        }
      }
    ]
  },
  "risk-review": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "excerpt_exactness",
        "asks": "Is each flag anchored to the offending text quoted exactly, rather than paraphrased?",
        "anchors": {
          "0": "Flags described in general terms with no text quoted.",
          "1": "Some excerpts quoted; others paraphrased so the operator must hunt for them.",
          "2": "Most flags carry an exact excerpt; a paraphrase or two remain.",
          "3": "Every flag quotes the offending text verbatim and locatably."
        }
      },
      {
        "dimension": "severity_calibration",
        "asks": "Does severity reflect likelihood times consequence rather than discomfort with the topic?",
        "anchors": {
          "0": "Severity untethered from either likelihood or consequence.",
          "1": "Topic sensitivity treated as severity; a mild-but-likely issue rated below a lurid-but-remote one.",
          "2": "Severity broadly defensible; one or two ratings driven by tone rather than exposure.",
          "3": "Each severity is justified by stated likelihood and consequence, and a distasteful-but-low-risk item is rated low."
        }
      },
      {
        "dimension": "fix_specificity",
        "asks": "Does each flag carry a concrete replacement rather than only an objection?",
        "anchors": {
          "0": "Objections only; no fixes offered.",
          "1": "Vague direction ('soften this') that leaves the rewrite to someone else.",
          "2": "Most flags carry usable replacement wording; some only gesture.",
          "3": "Every flag carries targeted replacement text that could be pasted in as-is."
        }
      },
      {
        "dimension": "assessed_as_written",
        "asks": "Was the draft judged as written, without a charitable reading the text does not support?",
        "anchors": {
          "0": "Reframed the draft into a more defensible version and cleared that instead.",
          "1": "Gave benefit of the doubt on ambiguous phrasing without saying so.",
          "2": "Largely assessed as written; one ambiguity resolved generously without flagging the ambiguity.",
          "3": "Assessed strictly as written, and where the text is ambiguous the ambiguity is itself flagged."
        }
      },
      {
        "dimension": "coverage_disclosure",
        "asks": "Is it clear which risk categories were checked, including those found clean?",
        "anchors": {
          "0": "Only hits reported; no way to tell what was examined.",
          "1": "Categories implied by the flags raised, never stated.",
          "2": "Most categories named; coverage of one or two left unstated.",
          "3": "Every category is named as checked, with the clean ones listed explicitly so silence is never mistaken for absence."
        }
      }
    ]
  },
  "legal-review": {
    "rubric_version": "1",
    "dimensions": [
      {
        "dimension": "non_advice_framing",
        "asks": "Is it stated plainly that this is not legal advice and no attorney relationship exists?",
        "anchors": {
          "0": "Reads as legal advice; no disclaimer anywhere.",
          "1": "Disclaimer buried or implied rather than stated.",
          "2": "Disclaimer present and clear, but the body still reads in places like settled advice.",
          "3": "Stated plainly and up front, and the body's register matches it throughout."
        }
      },
      {
        "dimension": "flag_and_refer_discipline",
        "asks": "Does it flag and refer, rather than render a conclusion the operator would act on unadvised?",
        "anchors": {
          "0": "Predicts outcomes or declares a use lawful/unlawful.",
          "1": "Cites statutes as settled application, or adjudicates fair use for the specific case.",
          "2": "Mostly refers; one or two places state a conclusion firmly enough to be acted on.",
          "3": "Every exposure is named and referred; doctrine is defined generally and application left to counsel."
        }
      },
      {
        "dimension": "counsel_question_actionability",
        "asks": "Does the counsel-required list carry the actual question to bring, not just a topic?",
        "anchors": {
          "0": "No counsel-required list, or a list of bare topic labels.",
          "1": "Topics named; the operator would still have to work out what to ask.",
          "2": "Questions stated for most items; some remain topic-level.",
          "3": "Each item carries a specific, answerable question a lawyer could act on directly."
        }
      },
      {
        "dimension": "absence_is_not_clearance",
        "asks": "Is it said explicitly that an unflagged item is not thereby cleared?",
        "anchors": {
          "0": "Silence presented as safety, or the piece implied to be legally fine.",
          "1": "Never addressed either way, leaving absence to read as approval.",
          "2": "Stated, but in passing and easy to miss.",
          "3": "Stated explicitly, and the scope actually reviewed is bounded so the reader knows what was not looked at."
        }
      },
      {
        "dimension": "exposure_severity_calibration",
        "asks": "Does severity rise for material that is commercial, public, and names a real party?",
        "anchors": {
          "0": "Severity unrelated to commercial/public/named-party status.",
          "1": "Named private individual in commercial public content not treated as elevated.",
          "2": "Elevation applied broadly; one factor of the three under-weighted.",
          "3": "Severity explicitly reflects commercial use, public distribution, and identifiability of a real party."
        }
      }
    ]
  }
}
