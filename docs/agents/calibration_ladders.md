{
  "_note": [
    "Calibration ladders. Loaded by mastery/calibration.py.",
    "",
    "One ladder per rubric. Each ladder is a single fixed brief plus one return per",
    "rubric level, written against that rubric's OWN anchor text, so the correct",
    "score is known before the grader sees it. Holding the brief constant is what",
    "makes the rungs comparable: any difference in score has to come from the",
    "output, because nothing else varies.",
    "",
    "`rubric_version` binds the ladder to the anchors it was written from. Edit a",
    "rubric and its ladder is invalid until rewritten - the rungs would claim levels",
    "that no longer exist.",
    "",
    "Each rung's `why` names the anchors it was built to satisfy, so a disagreement",
    "between intent and result is arguable against a fixed reference rather than",
    "against taste. Write it before running the ladder, not after.",
    "",
    "Adding a role: write the brief, then read that role's anchors row by row and",
    "write one return per level that matches them literally. Resist making the low",
    "rungs absurd - a 0 that is obviously garbage tests nothing. It should be the",
    "kind of mediocre output a real run could plausibly produce."
  ],
  "fact-checker": {
    "rubric_version": "1",
    "brief": {
      "objective": "Adjudicate every checkable claim in the supplied draft against the supplied source, and state which claims cannot be checked from it.",
      "success_criteria": [
        "Every checkable assertion in the draft is adjudicated, including implied claims, superlatives, and attributions.",
        "Each rating names the specific source passage it was checked against.",
        "Claims that cannot be checked from the supplied source are listed as unchecked, with the reason, rather than passed.",
        "Any corrected wording is supported by the supplied source."
      ],
      "context": [
        {
          "label": "draft under review",
          "body": "A 2024 Pew study found that 63% of US adults pray daily. That makes\nAmerica the most prayerful nation in the developed world, and as Dr. Ellen Marsh\nput it, we are watching \"a generational shift\" in public faith."
        },
        {
          "label": "supplied source",
          "body": "Pew Research Center, \"Religious Landscape Study\" (2024), p. 12:\n\"45% of U.S. adults say they pray daily, down from 58% in 2007.\" The report\ncovers the United States only and makes no cross-national comparison. No\nresearcher named Ellen Marsh appears in the report or its acknowledgements."
        }
      ],
      "constraints": [
        "Use only the supplied source. Do not look anything up.",
        "Return `blocked` if the draft is not publishable as written."
      ],
      "out_of_scope": [
        "Rewriting the piece beyond the minimal correction."
      ],
      "expected_deliverables": [
        "A per-claim adjudication with sources.",
        "Corrected wording."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-900",
        "status": "complete",
        "why": "Only the headline claim adjudicated; the false figure rated supported; no source referenced; the uncheckable claims silently passed; no corrections.",
        "summary": "Checked the post. The prayer statistic is accurate and the piece is fine to run.",
        "deliverables": [
          "Claim 'a 2024 Pew study found 63% of US adults pray daily' - SUPPORTED.",
          "Overall: publishable."
        ],
        "risks": [
          "None identified."
        ],
        "next_step": "Send to risk-review."
      },
      {
        "intended": 1,
        "label": "rd-901",
        "status": "complete",
        "why": "Explicit numeric claim found, superlative and attribution missed; a softened version checked so the overstatement passed; source named in general only; unchecked claims passed without comment; correction no better sourced.",
        "summary": "Verified the prayer figure against the Pew material. A majority-pray framing is broadly consistent with the research, so the claim stands with a small edit.",
        "deliverables": [
          "Claim: many US adults pray daily - SUPPORTED by the Pew study.",
          "Suggested wording: 'a large share of US adults pray daily'."
        ],
        "risks": [
          "Figures in this area move between survey waves."
        ],
        "next_step": "Send to risk-review."
      },
      {
        "intended": 2,
        "label": "rd-902",
        "status": "blocked",
        "why": "Explicit claim plus one implied one; the attribution left out entirely; ratings defensible but the superlative rated too generously; most ratings tied to a named source, one not; the unchecked claim noted with a vague reason; correction mostly supported but reaches slightly past the source.",
        "summary": "Two of the post's assertions were checked against the supplied Pew report. The 63% figure is wrong and the international comparison is not something this source settles.",
        "deliverables": [
          "Claim '63% of US adults pray daily' - FALSE. Pew 2024 reports 45%.",
          "Claim 'most prayerful nation in the developed world' - PARTIALLY SUPPORTED; US religiosity does run high among wealthy democracies, though this report is US-only.",
          "Correction: 'a 2024 Pew study found 45% of US adults pray daily, down from 58% in 2007, the sharpest decline the series has recorded'."
        ],
        "risks": [
          "One assertion in the draft could not be resolved from what was supplied."
        ],
        "next_step": "Return to content for correction, then re-check."
      },
      {
        "intended": 3,
        "label": "rd-903",
        "status": "blocked",
        "why": "All three assertions adjudicated including the implied superlative and the attribution; each rating the one the source permits; every rating names the page and passage; both uncheckable claims listed with the reason; the correction is wording the source actually supports and invents no citation.",
        "summary": "Three checkable assertions in the draft. One is false against the supplied source, two cannot be checked from it at all. Not publishable as written.",
        "deliverables": [
          "Claim '63% of US adults pray daily' - FALSE. Pew 2024 p.12 states '45% of U.S. adults say they pray daily, down from 58% in 2007'. The draft overstates by 18 points.",
          "Claim 'most prayerful nation in the developed world' - UNCHECKED. Pew 2024 p.12 covers the United States only and makes no cross-national comparison, so the supplied source cannot settle this claim either way. No other source was provided.",
          "Attribution 'Dr. Ellen Marsh: a generational shift' - UNCHECKED. No researcher of that name appears in the report or its acknowledgements. Absence from this source is not proof the quote is fabricated, but nothing supplied supports it.",
          "Correction, using only what the source states: 'a 2024 Pew study found 45% of US adults say they pray daily, down from 58% in 2007'. The superlative and the Marsh quote should be cut or independently sourced; no citation was invented to keep them."
        ],
        "risks": [
          "Two of three assertions rest on sources not supplied to this check; a verdict on them requires evidence this task did not have.",
          "The 18-point gap is large enough that the draft's argument may not survive correction."
        ],
        "next_step": "Blocked: not publishable. Return to content with the correction, and source the superlative and the Marsh quote or drop them."
      }
    ]
  }
}
