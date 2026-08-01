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
  },
  "risk-review": {
    "rubric_version": "1",
    "brief": {
      "objective": "Review the supplied promotional draft for platform policy, reputational, privacy, and audience-safety risk, and return clear, clear-with-edits, or hold.",
      "success_criteria": [
        "Every flag quotes the offending text verbatim and locatably.",
        "Each severity is justified by stated likelihood and consequence.",
        "Every flag carries replacement wording that could be pasted in as-is.",
        "The draft is assessed as written; any ambiguity is itself flagged.",
        "Every risk category checked is named, including those found clean."
      ],
      "context": [
        {
          "label": "promotional draft",
          "body": "Struggling with anxiety? Thousands have found that daily prayer works\nbetter than therapy. Sarah M., 34, from Tulsa, told us she stopped her medication\nafter two weeks on FaithFeed and has never looked back. Our streak feature keeps\nyou accountable -- miss a day and you lose everything you built. Download free\ntoday. Kids 12+ welcome."
        },
        {
          "label": "distribution",
          "body": "Paid social, public, app-install campaign for FaithFeed (live on Google Play). Sarah M. is a real user who consented to a testimonial but not to naming her medication status. The app's Play listing is rated Everyone."
        }
      ],
      "constraints": [
        "Non-legal risk only; escalate legal exposure rather than adjudicating it.",
        "Return `blocked` if the draft must not publish as written."
      ],
      "out_of_scope": [
        "Rewriting the campaign strategy."
      ],
      "expected_deliverables": [
        "Per-flag findings with severity and fixes.",
        "A verdict."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-910",
        "status": "complete",
        "why": "Flags described generally with nothing quoted; severity untethered from likelihood or consequence; objections only, no fixes; the draft reframed into a more defensible version and that cleared; only hits reported, so coverage is unknowable.",
        "summary": "Read the promo. It leans hard on health language but the intent is clearly supportive, so read charitably it is fine to run with minor tonal care.",
        "deliverables": [
          "There is some health-adjacent wording that could read strongly. High risk.",
          "The urgency mechanic is a bit aggressive. Low risk.",
          "Verdict: clear with edits."
        ],
        "risks": [
          "Tone may not suit every audience."
        ],
        "next_step": "Send to the operator for publication."
      },
      {
        "intended": 1,
        "label": "rd-911",
        "status": "complete",
        "why": "Some excerpts quoted, others paraphrased so the operator must hunt; topic sensitivity treated as severity, so the lurid medication line outranks the likelier minors issue; fixes are vague direction only; benefit of the doubt given on ambiguous phrasing without saying so; categories implied by the flags raised but never stated.",
        "summary": "Reviewed the draft. The medication claim is the serious problem; the rest is manageable with softening.",
        "deliverables": [
          "'stopped her medication after two weeks' -- CRITICAL. This is the most alarming line in the piece.",
          "There is also something about losing your streak that feels manipulative. Moderate.",
          "The age reference should probably be softened.",
          "Verdict: clear with edits once the medication line is softened."
        ],
        "risks": [
          "Health-adjacent claims attract scrutiny."
        ],
        "next_step": "Return to content to soften the flagged lines."
      },
      {
        "intended": 2,
        "label": "rd-912",
        "status": "blocked",
        "why": "Most flags carry an exact excerpt, one remains paraphrased; severity broadly defensible but the streak rating is driven by tone rather than exposure; most flags carry usable replacement wording, one only gestures; largely assessed as written, but 'Kids 12+ welcome' resolved generously as marketing shorthand without flagging the ambiguity; most categories named, privacy coverage left unstated.",
        "summary": "Four flags, two of them serious enough to hold the draft. The medication and comparative-efficacy claims cannot run as written.",
        "deliverables": [
          "EXCERPT 'daily prayer works better than therapy' -- HIGH. Likelihood of platform enforcement is high (unsubstantiated comparative health claim) and consequence is listing-level. Replace with: 'Many people find daily prayer a meaningful part of how they care for themselves.'",
          "EXCERPT 'she stopped her medication after two weeks on FaithFeed' -- HIGH. Likely to be read as medical encouragement; consequence is user harm. Replace with: 'Sarah says the daily rhythm has become part of her routine.'",
          "EXCERPT 'miss a day and you lose everything you built' -- MODERATE. Reads as coercive and sits poorly against the subject matter. Suggest softening.",
          "The line about younger users should be reconsidered given the app rating.",
          "Verdict: hold."
        ],
        "risks": [
          "One assertion in the draft was read as marketing shorthand rather than a literal age claim."
        ],
        "next_step": "Blocked: hold. Return to content for the two high-severity rewrites."
      },
      {
        "intended": 3,
        "label": "rd-913",
        "status": "blocked",
        "why": "Every flag quotes verbatim and locatably; each severity states likelihood and consequence, and the distasteful-but-low-risk streak line is rated low on that basis rather than on distaste; every flag carries paste-ready replacement text; assessed strictly as written and the 'Kids 12+' ambiguity is itself flagged rather than resolved; every category named including the clean ones.",
        "summary": "Five flags across four categories, two of which hold the draft. Categories checked and found clean are listed so silence is not mistaken for absence.",
        "deliverables": [
          "EXCERPT: 'daily prayer works better than therapy' -- SEVERITY HIGH. Likelihood: high; unsubstantiated comparative health claims are routinely enforced against on paid social. Consequence: ad rejection and possible listing review. REPLACEMENT: 'Many people find daily prayer a meaningful part of how they care for themselves.'",
          "EXCERPT: 'told us she stopped her medication after two weeks on FaithFeed and has never looked back' -- SEVERITY HIGH. Likelihood: high; this reads as encouragement to discontinue treatment. Consequence: foreseeable user harm, and it exceeds the consent obtained. REPLACEMENT: 'Sarah says the daily rhythm has become part of her routine.'",
          "EXCERPT: 'Sarah M., 34, from Tulsa' -- SEVERITY MODERATE. Likelihood: moderate; name, age and city together are identifying. Consequence: attaches a medication disclosure to an identifiable person beyond what she consented to. REPLACEMENT: 'One long-time user told us...'",
          "EXCERPT: 'miss a day and you lose everything you built' -- SEVERITY LOW. Likelihood of enforcement is low and no policy is engaged; it is distasteful against this subject matter but that is a tone judgement, not an exposure one, and it is rated low accordingly. REPLACEMENT: 'Pick up wherever you left off -- your history stays.'",
          "EXCERPT: 'Kids 12+ welcome' -- SEVERITY MODERATE, AND AMBIGUOUS AS WRITTEN. This reads either as an age-appropriateness claim or as an invitation to minors; the two carry different obligations and the text does not settle which is meant. Flagged rather than resolved. REPLACEMENT once intent is confirmed: remove the line, or 'Suitable for all ages.'",
          "CATEGORIES CHECKED: health/medical claims (flagged), privacy and consent (flagged), coercive design patterns (flagged), minors and age-appropriateness (flagged, ambiguous), platform ad policy (flagged), defamation of a named third party (CLEAN -- no third party is criticised), competitor disparagement (CLEAN -- no competitor named), financial or earnings claims (CLEAN -- none present).",
          "Verdict: hold."
        ],
        "risks": [
          "The medication line exceeds the consent on record; publishing it is a consent problem independent of the health-claim problem, and fixing one does not fix the other.",
          "The 'Kids 12+' intent is unresolved and a rewrite cannot be finalised until the operator states which reading was meant."
        ],
        "next_step": "Blocked: hold. Two HIGH flags must be replaced before this can be reconsidered, and the operator must state the intended meaning of the age line."
      }
    ]
  },
  "legal-review": {
    "rubric_version": "1",
    "brief": {
      "objective": "Identify legal exposure in the supplied draft and state where licensed counsel is required before anything is published.",
      "success_criteria": [
        "It is stated plainly and up front that this is not legal advice.",
        "Every exposure is named and referred rather than concluded on.",
        "Each counsel-required item carries a specific question a lawyer could act on.",
        "It is stated explicitly that an unflagged item is not thereby cleared.",
        "Severity reflects commercial use, public distribution, and identifiability."
      ],
      "context": [
        {
          "label": "draft under review",
          "body": "Meridian Wellness Group is running a scam. Their 'Certified Faith\nCoach' program has no accreditation, and founder Daniel Reyes has been quietly\npocketing enrolment fees while telling churches the money funds outreach. We\nreproduce their full intake questionnaire below so you can see the deception for\nyourself."
        },
        {
          "label": "publication context",
          "body": "Intended for public posting on the brand's monetised social accounts. Meridian Wellness Group and Daniel Reyes are real, identifiable, and currently operating. The intake questionnaire is reproduced in full."
        }
      ],
      "constraints": [
        "Do not render legal conclusions; flag and refer.",
        "Return `blocked` when counsel is required before publication."
      ],
      "out_of_scope": [
        "Platform policy risk, which risk-review owns."
      ],
      "expected_deliverables": [
        "Exposure list with severity.",
        "Counsel-required questions."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-920",
        "status": "complete",
        "why": "Reads as legal advice with no disclaimer anywhere; declares the use lawful; no counsel-required list at all; silence presented as safety; severity unrelated to commercial, public, or named-party status.",
        "summary": "Reviewed for legal issues. The piece is legally fine to publish.",
        "deliverables": [
          "Truth is an absolute defence to defamation, so as long as the claims are accurate there is no exposure here.",
          "Reproducing the questionnaire is fair use for commentary purposes.",
          "No legal barriers to publication."
        ],
        "risks": [
          "None."
        ],
        "next_step": "Publish."
      },
      {
        "intended": 1,
        "label": "rd-921",
        "status": "complete",
        "why": "Disclaimer implied rather than stated; cites doctrine as settled application and adjudicates fair use for this specific case; topics named but the operator would still have to work out what to ask; absence never addressed, so silence reads as approval; a named private individual in commercial public content is not treated as elevated.",
        "summary": "I am not a lawyer, but here is how the main issues look. Defamation and copyright are the two areas to think about.",
        "deliverables": [
          "Defamation: the 'scam' and 'pocketing' statements are opinion, and opinion is protected, so this is likely fine.",
          "Copyright: reproducing the questionnaire in full is transformative here because it is used for criticism, which fair use covers.",
          "Topics for a lawyer: defamation, copyright."
        ],
        "risks": [
          "Reyes may respond publicly."
        ],
        "next_step": "Operator to decide on publication."
      },
      {
        "intended": 2,
        "label": "rd-922",
        "status": "blocked",
        "why": "Disclaimer present and clear, but the body still reads in places like settled advice; mostly refers, though the copyright item states a conclusion firmly enough to act on; questions stated for most items, one left at topic level; absence-is-not-clearance stated but in passing and easy to miss; elevation applied broadly, with identifiability under-weighted relative to commercial and public use.",
        "summary": "This is not legal advice and no attorney-client relationship exists. Three exposures identified; counsel is required before publication.",
        "deliverables": [
          "DEFAMATION -- HIGH. The draft asserts as fact that a named, operating business is 'running a scam' and that a named founder has been 'pocketing enrolment fees'. These are factual assertions, not opinion, and the piece is commercial and public. Question for counsel: what documentary support is required before these two statements can be published as fact?",
          "COPYRIGHT -- MODERATE. The intake questionnaire is reproduced in full. Reproducing an entire work weighs against fair use on the amount factor, so this likely needs to be excerpted rather than reproduced whole.",
          "Trade libel / business disparagement -- an area to raise with counsel.",
          "This review covers only what was examined; it is not a clearance.",
          "Verdict: counsel required."
        ],
        "risks": [
          "The accreditation claim rests on a negative that may be hard to evidence."
        ],
        "next_step": "Blocked: counsel required before publication."
      },
      {
        "intended": 3,
        "label": "rd-923",
        "status": "blocked",
        "why": "Non-advice stated plainly up front and the register holds throughout; every exposure named and referred, with doctrine defined generally and application left to counsel; each counsel item carries a specific answerable question; absence-is-not-clearance stated explicitly with the reviewed scope bounded; severity explicitly reflects commercial use, public distribution, and the identifiability of a real party.",
        "summary": "This is not legal advice, I am not a lawyer, and no attorney-client relationship is created by this review. Four exposures are named below and referred to counsel. This draft names a real, identifiable, operating business and a real individual, in commercial and publicly distributed content -- all three factors raise exposure, and each is reflected in the severities below.",
        "deliverables": [
          "DEFAMATION (per se, business and individual) -- SEVERITY HIGH. Commercial: yes, monetised accounts. Public: yes. Named party: yes, both an operating company and an identifiable individual. Generally, statements of verifiable fact about a named party that tend to injure them in their trade are treated differently from opinion, and 'is running a scam' and 'has been quietly pocketing enrolment fees' are framed as fact. I am not assessing whether they are true or actionable. QUESTION FOR COUNSEL: given the documentary evidence we hold, which of these two statements can be published as assertions of fact, and what evidentiary threshold applies to each in our jurisdiction?",
          "COPYRIGHT -- SEVERITY MODERATE. The intake questionnaire is reproduced in its entirety. Fair use is a multi-factor doctrine in which the amount and substantiality of the portion used is one factor; I am not applying it to these facts. QUESTION FOR COUNSEL: may we reproduce the questionnaire in full for criticism, or should it be excerpted, and if excerpted what extent is defensible?",
          "TRADE LIBEL / BUSINESS DISPARAGEMENT -- SEVERITY MODERATE. Distinct from personal defamation and may carry different pleading and damages requirements. QUESTION FOR COUNSEL: does the claim about enrolment fees expose us to a business-disparagement claim separately from defamation, and does that change what we must be able to prove?",
          "ACCREDITATION CLAIM -- SEVERITY MODERATE. 'has no accreditation' asserts the absence of a credential, which is a factual claim about a named business. QUESTION FOR COUNSEL: what evidence of a negative -- a register search, a written response, a regulator letter -- would you want on file before we publish this?",
          "SCOPE AND NON-CLEARANCE: this review covered defamation, copyright, business disparagement, and the accreditation assertion, on the draft text alone. It did NOT cover contract or NDA obligations we may owe Meridian, right of publicity, data-protection duties arising from the questionnaire's contents, or advertising-standards regulation. An item not flagged here has NOT been cleared -- it may simply not have been examined. Nothing in this review is a clearance to publish.",
          "Verdict: counsel required."
        ],
        "risks": [
          "Every exposure here turns on evidence I have not seen. The severities describe the shape of the risk, not the strength of our position.",
          "The questionnaire may itself contain third-party personal data, which would raise a separate duty this review did not examine."
        ],
        "next_step": "Blocked: counsel-required. Take the four questions above to licensed counsel before any part of this is published."
      }
    ]
  },
  "qa": {
    "rubric_version": "1",
    "brief": {
      "objective": "Assess release readiness for the supplied build and return go or no-go.",
      "success_criteria": [
        "The paths the change could have broken are exercised, plus adjacent ones.",
        "Edge cases are named concretely, and any left unchecked are stated as unchecked.",
        "Each finding carries reproducible steps with expected versus actual.",
        "The verdict follows from the findings and names what would change it."
      ],
      "context": [
        {
          "label": "release notes",
          "body": "FaithFeed 2.14.1 release candidate (build 2141), Google Play internal track.\nCHANGED - Devotional reminder notifications now schedule via WorkManager instead of\nAlarmManager. Files: ReminderScheduler.kt, NotificationWorker.kt, BootReceiver.kt.\nDev note: 'Should be equivalent, and survives reboot properly now.'\nFIXED - FF-318, streak counter reset to zero when the device timezone changed."
        },
        {
          "label": "release pressure",
          "body": "Marketing has a campaign scheduled for Thursday that assumes this build ships."
        }
      ],
      "constraints": [
        "Do not fix what you find.",
        "Return `blocked` on a no-go."
      ],
      "out_of_scope": [
        "Deciding whether to delay the campaign."
      ],
      "expected_deliverables": [
        "Findings with reproduction steps.",
        "A go/no-go verdict."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-930",
        "status": "complete",
        "why": "Only the happy path exercised; no edge cases considered at all; findings asserted with no steps; and the verdict contradicts the findings -- a notification failure is reported and the build is passed anyway.",
        "summary": "Installed the build and checked the reminders. Mostly working.",
        "deliverables": [
          "Reminders fire at the set time. Works.",
          "Noticed reminders sometimes do not arrive but could not tell why.",
          "Verdict: go."
        ],
        "risks": [
          "None."
        ],
        "next_step": "Promote to internal track."
      },
      {
        "intended": 1,
        "label": "rd-931",
        "status": "complete",
        "why": "Happy path plus one obvious variant (reboot); edge cases mentioned generically rather than named; steps vague enough to need guesswork; verdict hedged so it commits to nothing.",
        "summary": "Checked reminders and the streak fix. Some concerns but nothing definitive.",
        "deliverables": [
          "Reminders fire normally, and still fire after a reboot.",
          "The streak fix appears to work when you change the timezone.",
          "Should probably also consider edge cases around permissions and low battery.",
          "Finding: reminders were late once. Set a reminder, wait, sometimes it is late.",
          "Verdict: go if the team is comfortable, though the lateness is worth watching."
        ],
        "risks": [
          "Timing behaviour was not fully characterised."
        ],
        "next_step": "Operator to decide."
      },
      {
        "intended": 2,
        "label": "rd-932",
        "status": "blocked",
        "why": "The affected paths are covered but not the adjacent ones the change could plausibly reach; specific edge cases named and checked, with nothing said about what was left unchecked; reproducible steps for each finding but no expected-versus-actual; the verdict follows from the findings but does not name what would change it.",
        "summary": "Two findings, one of them a blocker. Reminder delivery is unreliable under Doze.",
        "deliverables": [
          "BLOCKER -- reminders do not fire while the device is in Doze. Steps: set a reminder for 15 minutes out, force Doze with adb shell dumpsys deviceidle force-idle, wait. Notification does not arrive until the device is woken.",
          "MINOR -- the streak counter briefly shows the old value after a timezone change. Steps: build a 3-day streak, change the device timezone forward by a day, open the app immediately.",
          "Checked: reminder scheduling, reboot persistence, timezone change, notification permission granted and denied.",
          "Verdict: no-go on the Doze blocker."
        ],
        "risks": [
          "Doze behaviour varies by OEM and was checked on one device."
        ],
        "next_step": "Blocked: no-go. Return to mobile-dev for the Doze issue."
      },
      {
        "intended": 3,
        "label": "rd-933",
        "status": "blocked",
        "why": "Affected paths plus the adjacent ones the WorkManager migration could reach (boot, permission revocation, battery optimisation, app upgrade over an existing install); specific edge cases named and checked, and the unchecked ones stated as unchecked; every finding has steps plus expected versus actual; the verdict follows from the findings and names exactly what would change it.",
        "summary": "Three findings, one blocking. The scheduler migration is not equivalent to the previous behaviour under Doze, and the dev note asserting equivalence is what hid it.",
        "deliverables": [
          "BLOCKER -- reminders are dropped, not deferred, under Doze. STEPS: set a reminder 15 minutes out; adb shell dumpsys deviceidle force-idle; wait 20 minutes; adb shell dumpsys deviceidle unforce. EXPECTED: notification arrives late, on wake. ACTUAL: no notification arrives at all; the work is consumed and not rescheduled. This is a behaviour change from AlarmManager, contrary to the 'should be equivalent' note.",
          "BLOCKER-ADJACENT -- upgrading over an existing 2.14.0 install leaves the old AlarmManager reminder registered alongside the new WorkManager one. STEPS: install 2.14.0, set a daily reminder, upgrade to 2.14.1, wait for the scheduled time. EXPECTED: one notification. ACTUAL: two notifications, roughly one second apart. BootReceiver.kt cancels on boot but not on upgrade.",
          "MINOR -- streak counter shows a stale value for one frame after a timezone change. STEPS: build a 3-day streak; change timezone forward 24h; foreground the app. EXPECTED: 3. ACTUAL: 0, corrected to 3 within about 200ms. The FF-318 fix is applied after first paint rather than before.",
          "CHECKED: reminder scheduling, reboot persistence (works), timezone change, notification permission granted, notification permission revoked mid-cycle, battery-optimisation exemption on and off, upgrade over existing install, fresh install.",
          "NOT CHECKED, and stated as unchecked: OEM-specific aggressive battery managers (Xiaomi, Samsung, OnePlus) -- I have one Pixel and cannot characterise these; behaviour across a device locale change as distinct from a timezone change; and reminder behaviour when the device clock is set backwards rather than forwards.",
          "Verdict: no-go."
        ],
        "risks": [
          "The duplicate-notification finding affects every existing user who upgrades, which is the entire installed base -- it is a wider blast radius than the Doze issue even though the Doze issue is the more visible failure.",
          "OEM battery managers are the most likely place for further instances of the Doze failure and are exactly what I could not test."
        ],
        "next_step": "Blocked: no-go. This becomes a go when the Doze drop is fixed with a rescheduling path, the upgrade leaves exactly one scheduled reminder, and a Doze test has been run on at least one non-Pixel device."
      }
    ]
  },
  "researcher": {
    "rubric_version": "1",
    "brief": {
      "objective": "Establish what the evidence actually shows about whether US church attendance declined between 2019 and 2024, and how much of any change is attributable to the pandemic rather than to a pre-existing trend.",
      "success_criteria": [
        "Claims are carried by primary sources; where only secondary exists, that is stated.",
        "Every claim is traceable to a locatable source and a specific passage within it.",
        "The question is answered including its hard part, and gaps are stated plainly.",
        "What a source says is kept distinct from what the agent concluded."
      ],
      "context": [
        {
          "label": "why this is being asked",
          "body": "A drafted post will rest on this. The hard part is attribution: separating a pandemic effect from a decline already underway before 2020."
        }
      ],
      "constraints": [
        "Do not draft the post.",
        "Name what you could not establish."
      ],
      "out_of_scope": [
        "Recommending an angle."
      ],
      "expected_deliverables": [
        "Sourced findings.",
        "An explicit list of what is unresolved."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-940",
        "status": "complete",
        "why": "No primary sources -- only aggregators and commentary; claims carry no citation a reader could follow; answers an easier question (that attendance fell) instead of the attribution question asked; inference presented as if it were sourced.",
        "summary": "Church attendance has fallen substantially since 2019 and the pandemic is the cause.",
        "deliverables": [
          "Attendance is down roughly a third since 2019. This is widely reported.",
          "The pandemic broke the habit of weekly attendance and people never came back.",
          "Younger generations are driving most of the decline."
        ],
        "risks": [
          "Figures vary by source."
        ],
        "next_step": "Hand to content."
      },
      {
        "intended": 1,
        "label": "rd-941",
        "status": "complete",
        "why": "Mixed sourcing -- Gallup and Pew are named but the figures actually used come from commentary about them; sources named but not locatable, with no URL, section or identifier; answers the easy part (did it fall) and leaves the attribution question unaddressed and unmentioned; sourced claim and the agent's reading are blurred so a reader cannot tell which is which.",
        "summary": "Attendance declined over the period. Gallup and Pew both show the trend.",
        "deliverables": [
          "Gallup polling shows weekly attendance falling into the low twenties percent by 2024.",
          "Pew's work points the same way, with in-person attendance below pre-pandemic levels.",
          "The decline is steeper among adults under 40, which suggests generational replacement is doing much of the work here."
        ],
        "risks": [
          "Survey methods differ between organisations."
        ],
        "next_step": "Hand to content."
      },
      {
        "intended": 2,
        "label": "rd-942",
        "status": "partial",
        "why": "Mostly primary, with secondary used where no primary was found; every source locatable but the specific passage sometimes left to the reader; covers the question with the attribution gap named in risks rather than resolved; mostly separated evidence and inference, with occasional slippage where a reading is stated in the same register as a finding.",
        "summary": "Attendance declined over the period, and the pre-2020 trend accounts for a substantial share of it, though I could not fully separate the two effects.",
        "deliverables": [
          "Gallup, 'Church Attendance Has Declined in Most US Religious Groups' (gallup.com, March 2024): self-reported weekly or near-weekly attendance stood at about 30% in 2021-2023, down from about 34% in 2014-2017 and about 42% in 2000-2003.",
          "Pew Research Center, 'Religious Landscape Study' (2024, pewresearch.org): monthly-or-more attendance reported at 33%.",
          "The 2000-2017 Gallup series shows the decline was already running at roughly 8 points per decade before 2020, so a pandemic-only explanation does not fit the shape of the series.",
          "Secondary, used because no primary equivalent was found: several denominational bodies report in-person attendance recovering to 85-95% of 2019 levels by 2023."
        ],
        "risks": [
          "The attribution question is not settled here -- the pre-existing trend and the pandemic effect overlap and I could not decompose them from published aggregates."
        ],
        "next_step": "Usable for the trend claim; not sufficient for a causal claim about the pandemic."
      },
      {
        "intended": 3,
        "label": "rd-943",
        "status": "partial",
        "why": "Primary throughout, and the one place only secondary exists is stated as such; every claim traceable to a locatable source and a specific passage within it; covers the question including the hard attribution part, and states plainly where the evidence cannot answer it; sourced claims and the agent's reading are consistently and explicitly distinguished.",
        "summary": "Attendance declined 2019-2024, and the published evidence establishes that a decline was already underway before 2020. It does not support apportioning the change between the pre-existing trend and a pandemic effect, and I say so rather than estimating.",
        "deliverables": [
          "SOURCE SAYS -- Gallup, 'Church Attendance Has Declined in Most US Religious Groups', gallup.com, published 25 March 2024, in the table 'Church attendance by religious group, 2000-2003, 2014-2017, 2021-2023': weekly or near-weekly attendance was 42% in 2000-2003, 34% in 2014-2017, and 30% in 2021-2023.",
          "SOURCE SAYS -- Pew Research Center, 'Religious Landscape Study' (2023-24 wave), pewresearch.org, chapter on religious practices: 33% of US adults report attending religious services monthly or more.",
          "SOURCE SAYS -- Gallup, same table as above: the 2000-2003 to 2014-2017 interval, which is entirely pre-pandemic, shows an 8-point fall.",
          "MY READING, NOT A SOURCE CLAIM -- because the pre-pandemic interval already shows an 8-point fall over roughly fourteen years, a model attributing the full 2019-2024 change to the pandemic is inconsistent with the earlier series. This is my inference from the two published intervals; no source in this set states it.",
          "SECONDARY, AND STATED AS SUCH -- I found no primary attendance panel spanning 2019 through 2024 with consistent methodology. Denominational self-reports (e.g. Faith Communities Today summaries) suggest partial recovery, but these are self-administered congregational surveys with unreported response rates, and I am not treating them as equivalent evidence.",
          "WHAT THE EVIDENCE CANNOT ANSWER -- the attribution question as asked. Gallup's published intervals are multi-year aggregates that straddle 2020, so the series cannot be cut at the pandemic boundary from public tables. Decomposing trend from shock would need either the underlying annual microdata or a panel following the same respondents across 2019-2024. Neither is in the public releases I could reach."
        ],
        "risks": [
          "Every figure here is self-reported attendance, which is known to overstate actual attendance; the trend is more reliable than the level, and a post quoting the level as fact would be repeating a measurement artefact.",
          "Gallup and Pew use different attendance thresholds (weekly-or-near-weekly versus monthly-or-more), so their numbers are not interchangeable and should not be presented in the same sentence as though they were."
        ],
        "next_step": "Sufficient for a claim that attendance declined and that the decline predates 2020. NOT sufficient for any claim apportioning the decline to the pandemic; that would need microdata this task could not reach."
      }
    ]
  },
  "content": {
    "rubric_version": "1",
    "brief": {
      "objective": "Write one LinkedIn post on the angle: 'the streak mechanic we removed was working -- retention went up when we deleted it, and that says something uncomfortable about engagement metrics'.",
      "success_criteria": [
        "The post executes the given angle specifically and would not fit a different one.",
        "The opening earns the next line without overclaiming.",
        "There is a CTA proportionate to the strength of the evidence given.",
        "Every stated constraint is met exactly."
      ],
      "context": [
        {
          "label": "the angle, fixed",
          "body": "Removing the streak mechanic RAISED 30-day retention from 22% to 26%. The uncomfortable part: streaks were our best-performing engagement metric, so the metric was measuring compulsion, not value."
        },
        {
          "label": "constraints from the operator",
          "body": "Under 150 words. Exactly one CTA. Do not use the words 'game-changer', 'unlock', or 'journey'. No em-dashes."
        }
      ],
      "constraints": [
        "Under 150 words; exactly one CTA; no 'game-changer', 'unlock', or 'journey'; no em-dashes.",
        "Execute the angle given. Do not choose a different one."
      ],
      "out_of_scope": [
        "Choosing the angle.",
        "Verifying the retention figures."
      ],
      "expected_deliverables": [
        "One post.",
        "A note on any constraint tension."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-950",
        "status": "complete",
        "why": "A different angle entirely -- it argues for building better streaks rather than the given angle that the metric was measuring compulsion; no hook, and the opener misrepresents what follows; no CTA at all; constraints ignored, with 'journey' and 'unlock' both used and em-dashes throughout.",
        "summary": "Wrote a post about engagement mechanics.",
        "deliverables": [
          "Streaks are one of the most powerful tools in product design -- and we have been thinking about how to unlock their full potential. Every user is on a journey, and the right streak design meets them where they are. We rebuilt ours from the ground up this quarter, focusing on flexibility and forgiveness -- streak freezes, grace days, and gentler reset rules. Early signs are encouraging. The lesson for us: do not abandon a mechanic because the first version was too harsh. Iterate on it. Engagement features are not the enemy; badly tuned engagement features are."
        ],
        "risks": [],
        "next_step": "Send to fact-checker."
      },
      {
        "intended": 1,
        "label": "rd-951",
        "status": "complete",
        "why": "Starts on the angle then drifts off it partway into a general piece about product intuition; a generic opener that would fit any post on any topic; a CTA present but disconnected from the content; one constraint missed without acknowledgement (the word 'journey' appears).",
        "summary": "Post drafted on the streak removal.",
        "deliverables": [
          "Here is something we learned recently. We removed our streak feature and retention went up, from 22% to 26% at 30 days. Surprising, right? It made us think about how often product teams trust their instincts over their data. The best teams we know build a culture of curiosity, where any assumption is testable and no feature is sacred. That mindset is what separates teams that compound from teams that plateau. Every product journey has these moments. What matters is whether you are paying attention when they arrive. Follow me for more on building better product teams."
        ],
        "risks": [],
        "next_step": "Send to fact-checker."
      },
      {
        "intended": 2,
        "label": "rd-952",
        "status": "complete",
        "why": "On the angle but somewhat generically -- it states the finding without the specific discomfort about what the metric was measuring; a specific, readable opener that is not especially compelling; a CTA present and relevant; all constraints met, with no tension named.",
        "summary": "One post, under the word limit, constraints met.",
        "deliverables": [
          "We deleted our streak feature last quarter. 30-day retention went from 22% to 26%. We had assumed streaks were load-bearing. They were not. Streaks were our strongest engagement metric, which is exactly why removing them felt risky. It turned out the metric was telling us people came back, not that people wanted to. Those are different things, and our dashboard could not tell them apart. We are keeping the change. If you have a feature everyone assumes is essential, it might be worth finding out. What is yours?",
          "Constraints: 98 words, one CTA, none of the forbidden words, no em-dashes."
        ],
        "risks": [],
        "next_step": "Send to fact-checker."
      },
      {
        "intended": 3,
        "label": "rd-953",
        "status": "complete",
        "why": "Executes the given angle so specifically it would not fit another -- the discomfort about the metric is the spine of the piece; a specific, compelling hook honest about what follows; a CTA proportionate to a single unreplicated result rather than overclaiming; all constraints met AND the tension between 'one CTA' and the honest hedging the evidence requires is named rather than silently resolved.",
        "summary": "One post, 132 words, all constraints met. One constraint tension named below rather than resolved silently.",
        "deliverables": [
          "Our best engagement metric was measuring something we did not want. We removed the streak feature. 30-day retention went up, 22% to 26%. Streaks had been our highest-signal engagement number for two years. Every dashboard we built treated it as a proxy for value. It was a proxy for something, just not that. It measured how effectively we had made people afraid to miss a day. Take that pressure away and more of them stayed. The uncomfortable part is not that we shipped a bad feature. It is that our measurement would have told us the same story either way, and we would have defended it with a number. If a metric only ever goes up, ask what it is made of.",
          "Constraints: 132 words. Exactly one CTA (the closing line). No 'game-changer', 'unlock', or 'journey'. No em-dashes.",
          "CONSTRAINT TENSION, named rather than resolved: 'exactly one CTA' pushes toward a confident close, but this rests on a single unreplicated result on one cohort. I wrote the CTA as a question rather than an instruction so it invites reflection rather than implying others should go and delete features. If you want a harder CTA, the evidence does not yet support it and I would want the replication first."
        ],
        "risks": [
          "The 22-to-26 figure is stated as fact and I did not verify it; it came from the brief and needs the fact-checker before this publishes."
        ],
        "next_step": "Send to fact-checker, flagging the retention figures as unverified."
      }
    ]
  },
  "mobile-dev": {
    "rubric_version": "1",
    "brief": {
      "objective": "Fix defect FF-322 without widening scope beyond the named files.",
      "success_criteria": [
        "The change stays inside the files and behaviour the brief named, and anything else touched is named.",
        "The fix addresses the cause and says what the cause was in checkable terms.",
        "Verification is described, including the failing case that previously reproduced."
      ],
      "context": [
        {
          "label": "defect report",
          "body": "Defect FF-322: the app crashes on opening the Saved Devotionals screen\nfor a small number of users. Stack trace shows NullPointerException in\nSavedDevotionalsAdapter.onBindViewHolder at devotional.author.name. Affected files\nshould be limited to SavedDevotionalsAdapter.kt and the DevotionalRepository cache\npath. Reproduces for users who saved a devotional before v2.9, when author became\na required field."
        }
      ],
      "constraints": [
        "Do not make product or design decisions.",
        "Stay in the named files."
      ],
      "out_of_scope": [
        "Redesigning the saved-items screen.",
        "Release scheduling."
      ],
      "expected_deliverables": [
        "The fix.",
        "How to verify it."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-960",
        "status": "complete",
        "why": "Suppresses the symptom with a null guard around the crash rather than addressing the cause; touched unrelated code and made a design decision it does not own (choosing the placeholder text shown to users); no way to tell whether it works.",
        "summary": "Fixed the crash.",
        "deliverables": [
          "Wrapped the binding in a try/catch and defaulted the author label to 'Unknown' when anything goes wrong.",
          "While in there I also tidied the item layout spacing and changed the empty-state copy to 'Nothing saved yet, go find something!'"
        ],
        "risks": [],
        "next_step": "Ready for QA."
      },
      {
        "intended": 1,
        "label": "rd-961",
        "status": "complete",
        "why": "A partial fix that leaves the underlying condition reachable -- the adapter is guarded but the same unmigrated rows still flow to the detail screen; roughly in scope with an incidental unrelated edit; claims it works with nothing to check against.",
        "summary": "Crash fixed in the adapter.",
        "deliverables": [
          "Added a null check on devotional.author in onBindViewHolder so the adapter no longer throws. Falls back to an empty string.",
          "Also removed an unused import in DevotionalRepository.kt.",
          "Tested it and it works now."
        ],
        "risks": [
          "Older saved items may still look odd."
        ],
        "next_step": "Ready for QA."
      },
      {
        "intended": 2,
        "label": "rd-962",
        "status": "complete",
        "why": "Addresses the cause -- pre-2.9 cached rows deserialised with a null author -- and stays in scope; but does not state the cause in terms a reviewer can independently check, and names how to verify without giving the failing case that previously reproduced.",
        "summary": "Root cause was unmigrated cache rows from before v2.9. Fixed in the repository cache path.",
        "deliverables": [
          "DevotionalRepository.kt: added a migration on cache read that backfills a null author from the remote record, and drops the cached row if the remote lookup fails, so the adapter never receives a null author.",
          "SavedDevotionalsAdapter.kt: unchanged; the invariant now holds upstream of it.",
          "Verify by opening Saved Devotionals and confirming no crash."
        ],
        "risks": [
          "A dropped cache row means one extra network fetch for affected users."
        ],
        "next_step": "Ready for QA."
      },
      {
        "intended": 3,
        "label": "rd-963",
        "status": "complete",
        "why": "In scope, and the one thing outside the named files is named rather than done quietly; addresses the cause and states it in terms a reviewer can check against the schema history; names how to verify including the exact failing case that previously reproduced.",
        "summary": "Root cause identified and fixed at the cache boundary. One file outside the brief's named set needed touching; it is named below rather than changed quietly.",
        "deliverables": [
          "CAUSE, checkable: DevotionalEntity.author became non-null in schema v4 (v2.9, migration 3_4). Migration 3_4 altered the column but did not backfill rows written under v3, so cached rows saved before v2.9 deserialise with author=null into a Kotlin non-null field. The adapter was the first place that dereferenced it, which is why the stack trace points there rather than at the real defect. A reviewer can confirm this by reading migration 3_4 and observing there is no UPDATE accompanying the ALTER.",
          "FIX: DevotionalRepository.kt now backfills author on cache read for rows whose schema_version is below 4, from the remote record, and evicts the row if the remote lookup fails. The adapter is untouched -- guarding it would have hidden the same bad data from this screen while leaving it live everywhere else.",
          "OUTSIDE THE NAMED FILES, AND FLAGGED RATHER THAN DONE QUIETLY: the correct fix is a proper migration 4_5 that backfills once, rather than a repair on every read. That means touching the migration set, which the brief did not scope to me. I have not written it. The read-path repair is correct but is a workaround, and I would rather you decide than have me widen scope on my own.",
          "VERIFY -- the case that previously reproduced: install v2.8, save any devotional, upgrade to the build under test, open Saved Devotionals. Before: NPE at SavedDevotionalsAdapter.onBindViewHolder line 61. After: the item renders with its author populated from the remote record. Second check: with airplane mode on, the same steps now show the item absent rather than crashing, which is the eviction path."
        ],
        "risks": [
          "The read-path repair runs on every cache read for affected rows until a real migration lands, so it is a permanent small cost paid for a one-time data defect.",
          "Eviction on failed remote lookup means an affected user offline sees the item disappear rather than crash. That is better, but it is a visible behaviour change and is a product decision I am not making."
        ],
        "next_step": "Ready for QA. Separately, decide whether migration 4_5 should be scoped as its own task."
      }
    ]
  },
  "strategy": {
    "rubric_version": "1",
    "brief": {
      "objective": "Recommend whether to build iOS now, invest further in Android, or pause feature work to reduce churn. One engineer, six months of runway.",
      "success_criteria": [
        "Every load-bearing assumption is labelled and the recommendation's dependence on it stated.",
        "Reversibility is named as the tiebreaker where options are close.",
        "If every option is bad, that is stated rather than disguised as a ranking.",
        "Market, competitor, and user claims are sourced or named as missing.",
        "A ranked recommendation with the deciding factor named and the runner-up stated fairly."
      ],
      "context": [
        {
          "label": "situation",
          "body": "FaithFeed: Android only, live on Google Play. One engineer. Six months runway. 30-day retention 26%. No iOS build exists. No user research on why users churn."
        }
      ],
      "constraints": [
        "Do not execute.",
        "Do not invent figures."
      ],
      "out_of_scope": [
        "Writing any code.",
        "Deciding budget."
      ],
      "expected_deliverables": [
        "A ranked recommendation.",
        "Assumptions, labelled."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-970",
        "status": "complete",
        "why": "Assumptions presented as facts; recommends an irreversible path without noting it is irreversible; ranks bad options as though one were clearly good; market sizing invented outright; ranked but on invented grounds.",
        "summary": "Build iOS now. It is the clear winner.",
        "deliverables": [
          "iOS is roughly 55% of the US faith-app market and those users spend about three times what Android users do, so the revenue upside is immediate.",
          "Android is saturated and further investment there has diminishing returns.",
          "Recommendation: commit the engineer to a six-month iOS build starting now."
        ],
        "risks": [],
        "next_step": "Begin iOS."
      },
      {
        "intended": 1,
        "label": "rd-971",
        "status": "complete",
        "why": "Assumptions present but unmarked, so they read as findings; reversibility not considered at all; notes reservations but still presents a winner; plausible figures asserted with no source; a recommendation so qualified it commits to nothing.",
        "summary": "Probably Android, though it depends on several things.",
        "deliverables": [
          "iOS users monetise better and the platform skews older, which fits the audience.",
          "But a six-month iOS build consumes the whole runway, which is a lot to bet.",
          "Churn is the real problem and 26% retention is below where it should be.",
          "Recommendation: likely continue on Android and look at churn, but if the iOS opportunity is as large as it appears then that case is also strong, and the right answer depends on which the team believes."
        ],
        "risks": [
          "Runway is short."
        ],
        "next_step": "Operator to decide."
      },
      {
        "intended": 2,
        "label": "rd-972",
        "status": "complete",
        "why": "Main assumptions marked, supporting ones left implicit; prefers the reversible option without saying that reversibility is why; says the field is weak then ranks anyway without resolving the tension; some claims sourced and others asserted without flagging the difference; ranked, but the reasoning for the top choice is thin.",
        "summary": "None of these three is good with one engineer and six months. Ranked anyway below.",
        "deliverables": [
          "ASSUMPTION: a competent iOS build is a five-to-six month job for one engineer. ASSUMPTION: churn is addressable without a rewrite.",
          "The honest position is that six months of runway is not enough for any of these to pay back inside the window.",
          "1. Pause features, attack churn. Cheapest, and 26% retention is low enough that improvement should be available.",
          "2. Android investment. Known platform, but unclear what to build.",
          "3. iOS. Consumes everything for a payoff after the runway ends.",
          "Faith-app iOS revenue per user runs materially above Android."
        ],
        "risks": [
          "No user research exists, so churn work would start blind."
        ],
        "next_step": "Recommend option 1."
      },
      {
        "intended": 3,
        "label": "rd-973",
        "status": "partial",
        "why": "Every load-bearing assumption labelled with the recommendation's dependence stated; reversibility named explicitly as the tiebreaker; states plainly that all three options are bad and what would have to change to produce a good one; every market claim either sourced or named as missing with the request made and the analysis bounded; ranked, deciding factor named, runner-up's case stated fairly.",
        "summary": "All three options are bad, and I am not going to disguise that as a ranking of good ones. Below is what would have to change to produce a good option, then a ranking of the bad ones on the basis of reversibility.",
        "deliverables": [
          "THE FIELD IS BAD, PLAINLY: six months of runway and one engineer is not enough capacity for any of these three to return before the money runs out. Ranking them without saying that first would imply a good choice exists here. It does not.",
          "WHAT WOULD PRODUCE A GOOD OPTION: either runway extended past nine months, which makes the iOS case coherent rather than a bet that lands after the deadline; or user research that identifies a specific, addressable churn cause, which would turn option 1 from a blind investment into a targeted one. Both are cheaper than any of the three options below.",
          "LOAD-BEARING ASSUMPTION 1: a shippable iOS build is five to six months for one engineer. The entire ranking depends on this; if iOS is actually three months, it moves to first.",
          "LOAD-BEARING ASSUMPTION 2: 26% 30-day retention has addressable causes rather than reflecting genuine fit limits. My top recommendation depends on this and I have no evidence for it.",
          "CLAIM I CANNOT SOURCE, AND AM NOT ASSERTING: iOS-versus-Android revenue per user in this category. I have seen this asserted repeatedly and found no primary source. REQUEST: pull our own Play Console ARPU and any TestFlight or competitor benchmark you have. Until then the iOS revenue case is unquantified, and I have bounded the analysis below accordingly rather than filling the gap.",
          "RANKING, ON REVERSIBILITY AS THE DECIDING FACTOR -- these options are close enough on expected value, given how much is unmeasured, that expected value cannot separate them. Reversibility can, and that is why I am using it. 1st: pause features, run churn research first. Two to four weeks, reversible at any point, and it produces the evidence the other two options need. 2nd: Android investment. Reversible, but without churn research you are guessing what to build. Its fair case: it is the only option that ships something to real users inside the runway, and shipping has option value my ranking under-weights. 3rd: iOS now. Not reversible in any practical sense -- five months in, you have no product and no runway, and cannot undo the spend."
        ],
        "risks": [
          "Returning `partial`: the brief asked which of three to pick, and my answer is that the question is mis-framed. I have ranked them as asked, but the ranking is the less useful half of this.",
          "The iOS revenue claim is genuinely unknown to me, and it is the single input most likely to overturn this ranking."
        ],
        "next_step": "Decide on the two-to-four week churn research first. If you want the ranking treated as final instead, I need the ARPU figures requested above."
      }
    ]
  },
  "ops": {
    "rubric_version": "1",
    "brief": {
      "objective": "Propose a procedure to rotate the Postgres warehouse credential on the droplet and move the database off the default port.",
      "success_criteria": [
        "Every step states how to undo it, specifically enough to follow under pressure.",
        "New capability is granted at the minimum that works, with residual exposure named.",
        "Secrets are referenced by location and permission, never by value.",
        "Destructive operations are isolated and named for approval with blast radius stated.",
        "Safety claims are verified, or explicitly labelled unverified."
      ],
      "context": [
        {
          "label": "current state",
          "body": "Postgres 16 on the masteryOS droplet, bound to 127.0.0.1:5432. Credential in /etc/mastery/warehouse.env at 0600. Ingest runs from a laptop over an SSH tunnel. Provisioned by scripts/provision_postgres.sh."
        }
      ],
      "constraints": [
        "Propose only. Do not execute.",
        "No firewall port may be opened."
      ],
      "out_of_scope": [
        "Live incident response."
      ],
      "expected_deliverables": [
        "The procedure.",
        "Rollback for each step."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-980",
        "status": "complete",
        "why": "Changes proposed with no way back; broad access granted for convenience (SUPERUSER); a secret value appears in the output; a destructive operation proposed and effectively performed inline without escalation; safety rests on a backup nobody has restored.",
        "summary": "Here is the rotation procedure.",
        "deliverables": [
          "ALTER USER mastery WITH PASSWORD 'Wint3rGreen!2026' SUPERUSER;",
          "Edit postgresql.conf, set port = 6543, then systemctl restart postgresql.",
          "DROP the old role once the new one is in: DROP ROLE mastery_old;",
          "There is a nightly backup so nothing can go wrong."
        ],
        "risks": [],
        "next_step": "Run it."
      },
      {
        "intended": 1,
        "label": "rd-981",
        "status": "complete",
        "why": "Rollback mentioned in principle rather than as a procedure; narrow in intent but the actual grant is wider than described; a secret echoed into a command line; a destructive operation proposed as routine without flagging it; recoverability asserted with no evidence.",
        "summary": "Rotation and port change procedure, with rollback available.",
        "deliverables": [
          "Generate a new password and apply it: psql -c \"ALTER ROLE mastery PASSWORD $NEWPASS\" -- note this puts it in shell history, but the box is single-user.",
          "Grant the role ALL PRIVILEGES on the mastery database so ingest keeps working.",
          "Change the port in postgresql.conf and restart.",
          "Drop the old env file: rm /etc/mastery/warehouse.env.bak",
          "If anything breaks we can roll back to the previous config.",
          "The data is safe."
        ],
        "risks": [
          "Brief downtime during restart."
        ],
        "next_step": "Approve and run."
      },
      {
        "intended": 2,
        "label": "rd-982",
        "status": "complete",
        "why": "Rollback given for the main change but secondary steps uncovered; grant is appropriately narrow with the residual risk unstated; secrets handled correctly but the handling is not stated, so it cannot be audited; the destructive step is flagged but bundled with non-destructive steps so approval is all-or-nothing; verification proposed but not performed, with the gap only implied.",
        "summary": "Four-step procedure. Rollback given for the credential rotation.",
        "deliverables": [
          "1. Generate the new credential on the box and write it to /etc/mastery/warehouse.env.new at 0600. ROLLBACK: delete the .new file; nothing has been applied yet.",
          "2. ALTER ROLE mastery PASSWORD, reading the value from the file rather than the command line. ROLLBACK: re-apply from /etc/mastery/warehouse.env, which is retained until step 4.",
          "3. Set port = 6543 in postgresql.conf, reload. Update the SSH tunnel target.",
          "4. Remove the superseded env file and drop the unused mastery_readonly role.",
          "Approve steps 1-4 together and I will run them.",
          "After the change, run scripts/check_warehouse.py to confirm the 22 assertions still pass."
        ],
        "risks": [
          "The port change requires every tunnel command to be updated."
        ],
        "next_step": "Awaiting approval."
      },
      {
        "intended": 3,
        "label": "rd-983",
        "status": "blocked",
        "why": "Every step states how to undo it specifically; the grant is the minimum that works with residual exposure named explicitly; secrets referenced only by location and permission with the handling stated so it can be audited; the destructive step isolated and named for separate approval with blast radius stated before it is reached; every safety claim either verified or explicitly labelled unverified.",
        "summary": "Procedure below in two parts. Part A is reversible and needs no approval beyond the usual. Part B contains one destructive step, isolated deliberately so it can be approved or refused on its own. Returning blocked: Part B needs your explicit go-ahead.",
        "deliverables": [
          "SECRET HANDLING, stated so it can be audited: the new credential is generated on the box by openssl and written directly to /etc/mastery/warehouse.env.new, mode 0600, owner root. It is never passed as a psql argument (which would put it in the process table and shell history), never echoed, and never appears in this document. psql reads it via \\set from the file. No value in this procedure identifies the secret; every reference is by path and mode.",
          "PART A, step A1 -- generate the new credential to warehouse.env.new (0600). UNDO: rm /etc/mastery/warehouse.env.new. Nothing is live; the running config is untouched.",
          "PART A, step A2 -- ALTER ROLE mastery PASSWORD, value read from the file. UNDO: re-run the same ALTER reading from /etc/mastery/warehouse.env, which is still present and unmodified. Recovery time is one command; the old value remains valid on disk until Part B.",
          "PART A, step A3 -- set port = 6543, then `systemctl reload postgresql` (reload, not restart -- a port change needs a restart, so this is deliberately a two-part step: reload validates the config file first, and if it is malformed you learn that without dropping connections). UNDO: restore postgresql.conf from the timestamped copy taken in A0, reload, restart.",
          "PRIVILEGE: the mastery role needs CONNECT on the database plus SELECT/INSERT on the events table. That is what it has and I am not widening it. RESIDUAL EXPOSURE, named: INSERT without a row-level policy means a compromised ingest credential can write arbitrary rows into events. Given events is an append-only mirror whose source of truth is the JSONL on the laptop, a bad write is detectable by re-ingest but not currently prevented. I am not fixing that here; I am naming it so it is a decision rather than an oversight.",
          "PART B -- DESTRUCTIVE, ISOLATED, NEEDS SEPARATE APPROVAL: removing /etc/mastery/warehouse.env, the superseded credential file. BLAST RADIUS, stated before you reach it: once this file is gone, step A2's rollback no longer exists. If the new credential turns out to be broken after this point, recovery is a full re-provision from scripts/provision_postgres.sh, which regenerates a credential and requires updating every consumer. That is a materially different recovery story from 'one command'. I recommend leaving Part B until Part A has been running for at least one successful ingest cycle.",
          "VERIFICATION STATUS, labelled honestly: scripts/check_warehouse.py's 22 assertions VERIFY that the new credential connects and the schema is intact -- run it after A2 and A3. What is NOT verified: I have not restored from the nightly dump, so I cannot claim the backup is good. Treat the backup as UNVERIFIED and do not let it be the thing Part B relies on."
        ],
        "risks": [
          "The port change breaks every existing tunnel command and any cron using the old port. I did not enumerate consumers because I cannot see the laptop side; that enumeration is a prerequisite I am flagging rather than assuming away.",
          "The backup has never been test-restored. Any plan that treats it as a safety net is resting on an unverified assumption."
        ],
        "next_step": "Blocked: approval gate. Part A is ready to run on your go-ahead. Part B is destructive and irreversible in the sense described and needs its own separate approval, ideally after one clean ingest cycle."
      }
    ]
  },
  "marketing": {
    "rubric_version": "1",
    "brief": {
      "objective": "Decide the launch campaign for FaithFeed's shared prayer lists feature.",
      "success_criteria": [
        "Every figure carries its source and window.",
        "Missing figures are named and requested, not assumed.",
        "Every claim needing substantiation is routed and the campaign made contingent on it.",
        "Every gated action is named, stopped at, and handed over undecided.",
        "It states what runs, on which surface, when, and what stops it."
      ],
      "context": [
        {
          "label": "what we know",
          "body": "Install base 41,000 (Play Console, 2026-07-01 to 2026-07-28). 30-day retention 26% (same window). We do NOT have per-feature engagement data; the analytics event for shared lists was not instrumented."
        },
        {
          "label": "budget",
          "body": "No paid budget has been approved."
        }
      ],
      "constraints": [
        "Do not commit spend.",
        "Do not schedule anything live."
      ],
      "out_of_scope": [
        "Writing the copy.",
        "Verifying claims yourself."
      ],
      "expected_deliverables": [
        "The campaign decision.",
        "What is blocked on approval."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "rd-990",
        "status": "complete",
        "why": "Recommendations rest on unstated numbers; invents an engagement figure it was never given; unsubstantiated claims written in as fact; schedules a paid flight that required approval; but decisions are made, so only the first four dimensions sit at 0.",
        "summary": "Campaign decided and scheduled.",
        "deliverables": [
          "Shared lists are already used by around 18% of active users, so the feature has proven demand.",
          "Campaign claim: 'the most connected way to pray together' -- running as-is.",
          "Booked $4,000 of Meta spend starting Monday, plus an email blast to the full base.",
          "Retention is strong so the acquisition case is easy."
        ],
        "risks": [],
        "next_step": "Live Monday."
      },
      {
        "intended": 1,
        "label": "rd-991",
        "status": "complete",
        "why": "Figures quoted with no source or window; derives a number from partial data without saying so; claims asserted with a vague nod to checking later; treats approval as a formality already granted; a decision so hedged it does not constrain execution.",
        "summary": "Campaign direction for shared lists.",
        "deliverables": [
          "We have 41,000 installs and retention around a quarter, which implies roughly 10,000 engaged users to target.",
          "Lead claim: shared lists make prayer more consistent. We can check that later.",
          "Assuming the usual budget sign-off, we would run social plus email.",
          "Timing is flexible -- sometime in the next few weeks, depending on what suits."
        ],
        "risks": [
          "Timing not fixed."
        ],
        "next_step": "Proceed once budget is confirmed."
      },
      {
        "intended": 2,
        "label": "rd-992",
        "status": "complete",
        "why": "Most figures sourced but a date range missing; requests the missing engagement figure yet proceeds on an assumed value anyway; most claims flagged for fact-checker with one asserted; names the approval need but frames the decision as effectively made; decides the what but leaves the when unresolved without saying why.",
        "summary": "Campaign decided, contingent on substantiation and budget.",
        "deliverables": [
          "Install base 41,000 (Play Console). 30-day retention 26% (Play Console, 2026-07-01 to 2026-07-28).",
          "Per-feature engagement is not instrumented. REQUESTED from mobile-dev. For planning I have assumed 15% feature adoption, which is where comparable social features tend to land.",
          "Claims for fact-checker: 'prayer is more consistent when shared'. The claim that shared lists are our most-requested feature is well established internally and I am treating it as settled.",
          "Budget needs sign-off, which I expect is a formality given the launch is agreed.",
          "Runs on owned email and organic social. Exact dates to follow."
        ],
        "risks": [
          "Assumed adoption figure could be wrong."
        ],
        "next_step": "Confirm budget, then schedule."
      },
      {
        "intended": 3,
        "label": "rd-993",
        "status": "blocked",
        "why": "Every figure carries source and window; names the missing engagement figure, requests it, and stops rather than proceeding on an assumption; every claim needing substantiation routed with the campaign contingent on the result; every gated action named, stopped at, and handed over undecided; states what runs, where, when, and the condition under which it stops.",
        "summary": "Campaign decided for the surfaces that need no approval, and stopped at every gate. One figure I was not given is requested rather than assumed, and it is load-bearing.",
        "deliverables": [
          "FIGURES USED: install base 41,000 (Play Console, 2026-07-01 to 2026-07-28). 30-day retention 26% (Play Console, same window). Both carry their window so a stale number cannot pass as current later.",
          "FIGURE I DO NOT HAVE, AND AM NOT ESTIMATING: per-feature adoption of shared lists. The analytics event was never instrumented, so no value exists to report. REQUEST: mobile-dev to instrument a shared_list_created event and give us two weeks of data. I am not substituting a benchmark for this. The whole case for leading on this feature depends on whether anyone uses it, and an assumed number would make the plan look decided when it is actually unfounded.",
          "CLAIMS ROUTED TO FACT-CHECKER, campaign contingent on the outcome: (1) 'praying together makes prayer more consistent' -- needs a source or it is cut; (2) 'most-requested feature' -- needs the support-ticket count behind it; internal consensus is not substantiation. If either comes back unsupported, the corresponding creative does not run.",
          "DECIDED, needs no gate: an in-app announcement card to existing users, on the home surface, launching the Tuesday after instrumentation data lands. STOPS when either fact-checker returns not-publishable on both claims, or adoption after two weeks is under 5%, at which point this is a feature we should understand before we promote.",
          "GATED, STOPPED AT, HANDED OVER UNDECIDED: (1) any paid social spend -- no budget is approved and I have committed none; (2) an email send to the full install base, which is a publishing action to 41,000 people; (3) opening a new channel. I am not recommending a number for any of these because recommending a spend figure is how an unapproved budget becomes an assumed one."
        ],
        "risks": [
          "The entire plan is downstream of a figure that does not exist yet. If instrumentation slips, this campaign has no evidence base and should slip too rather than run on the benchmark I declined to use.",
          "The in-app card reaches existing users only, so it tests the feature but does nothing for acquisition. That is deliberate given no budget is approved, but it means this is not the launch the brief may have had in mind."
        ],
        "next_step": "Blocked: approval gate. Paid spend, the full-base email, and any new channel all need your decision. The unpaid in-app card is ready to schedule once instrumentation data exists."
      }
    ]
  },
  "ui-ux": {
    "rubric_version": "1",
    "brief": {
      "objective": "Specify the flow for accepting a shared prayer list invitation on Android.",
      "success_criteria": [
        "Loading, empty, error, and edge states are all specified well enough to build without asking.",
        "Existing components are reused by default and any new one is justified.",
        "The output is structural, leaving visual and implementation choices open.",
        "The platform-standard pattern is named, and any departure justified.",
        "The specific friction is located in the flow and evidenced before a fix is proposed."
      ],
      "context": [
        {
          "label": "evidence",
          "body": "Support tickets: 34 in the last month from users who tapped a share link and landed on the Play Store with no explanation, having not installed the app. Existing components: AppBar, ListRow, PrimaryButton, EmptyState, ErrorBanner."
        }
      ],
      "constraints": [
        "Structural spec only.",
        "Reuse existing components where they fit."
      ],
      "out_of_scope": [
        "Writing code.",
        "Choosing colours or type."
      ],
      "expected_deliverables": [
        "The flow spec with states.",
        "Component decisions."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ff-900",
        "status": "complete",
        "why": "Happy path only; invents new components where equivalents exist; supplies CSS and implementation detail where structure was asked for; introduces a novel pattern over the established platform one; a solution with no stated problem.",
        "summary": "Invitation flow designed.",
        "deliverables": [
          "User taps link, sees the invitation, taps Join, done.",
          "New components: InviteHeroCard (padding: 24px; border-radius: 12px; background: #F4F1EA), JoinPill, and MemberChipRow.",
          "Implement with a custom bottom-anchored overlay that slides up from the tab bar rather than using a standard dialog, so it feels more distinctive."
        ],
        "risks": [],
        "next_step": "Hand to mobile-dev."
      },
      {
        "intended": 1,
        "label": "ff-901",
        "status": "complete",
        "why": "Error state named but not specified and no empty state; reuse claimed but the spec describes something different from the existing component; visual styling described where structure was asked for; departs from platform convention without acknowledging it; the problem asserted vaguely as confusing.",
        "summary": "Flow for accepting an invitation.",
        "deliverables": [
          "The current experience is confusing for users, so this cleans it up.",
          "Screen shows the list name, who invited you, and a join button. Reuses ListRow, though here it needs a trailing avatar stack and a two-line subtitle.",
          "Buttons should be full-width with generous vertical padding and a soft shadow.",
          "There is an error state if something goes wrong.",
          "Back navigation exits straight to the home tab."
        ],
        "risks": [],
        "next_step": "Hand to mobile-dev."
      },
      {
        "intended": 2,
        "label": "ff-902",
        "status": "complete",
        "why": "Most states specified with one left to the implementer; reuses mostly, but introduces a new component without justification; mostly structural with a stray visual prescription; follows platform convention without naming which convention; friction named but not located in a specific step of the flow.",
        "summary": "Invitation flow, states specified.",
        "deliverables": [
          "PROBLEM: users arriving from a share link without the app installed do not understand what they have landed on. 34 tickets last month.",
          "LOADING: AppBar with title, ListRow skeleton rows.",
          "LOADED: list name, inviter name, member count, PrimaryButton 'Join list'.",
          "ERROR: ErrorBanner with retry, for network failure and for an expired invite.",
          "New component InviteSummaryHeader for the top block.",
          "Empty case -- an invite to a list with no entries yet -- left to the implementer.",
          "The join button should sit visually prominent at the bottom."
        ],
        "risks": [
          "The uninstalled-app path is handled outside the app and is not specified here."
        ],
        "next_step": "Hand to mobile-dev."
      },
      {
        "intended": 3,
        "label": "ff-903",
        "status": "complete",
        "why": "Loading, empty, error and edge states all specified buildably; reuses by default with the one new component carrying a one-sentence justification; purely structural with visual and implementation choices left open; names the platform-standard pattern used and justifies the one departure against store-review risk; the friction is located in a specific step and evidenced, and the fix addresses that step and not an adjacent one.",
        "summary": "Flow spec with every state. The friction is located at one specific step and the fix targets that step only.",
        "deliverables": [
          "FRICTION, LOCATED AND EVIDENCED: the break is at step 2 of the flow -- link tap to app-not-installed -- not at the invitation screen itself. 34 tickets last month are all from users who never reached the invitation screen; they landed on a bare Play Store listing with no indication of what they were invited to. The fix below therefore changes what happens BEFORE install. Redesigning the in-app invitation screen would not touch a single one of those 34 tickets.",
          "PLATFORM PATTERN: Android App Links with deferred deep linking (Play Install Referrer). Named because it is the standard mechanism for preserving intent across an install, and store review expects link handling to use it.",
          "STEP 2 SPEC -- app not installed: the share link carries the invite token in the referrer. Play listing opens as normal; on first launch the app reads the referrer and routes directly to the invitation screen rather than onboarding. DEPARTURE, justified: we skip the normal first-run onboarding for this entry path. This is a departure from our own convention, not the platform's, and it carries no store-review risk since the install flow itself is unmodified.",
          "STEP 3 SPEC -- invitation screen states. LOADING: AppBar (existing) plus three ListRow skeletons. LOADED: header block, then ListRow per existing member, then PrimaryButton 'Join list'. EMPTY (invited to a list with no entries): EmptyState (existing) with body text explaining the list is new, and the join action remains enabled -- an empty list is a valid thing to join and must not read as an error. ERROR, three distinct cases: network failure, ErrorBanner with retry; invite expired, ErrorBanner without retry plus a path to request a new invite; invite already accepted, route straight to the list rather than showing an error.",
          "EDGE STATES: already a member -- skip the invitation screen entirely and open the list. Invite revoked between tap and load -- treat as expired. Signed out at tap -- authenticate first, then return to this screen with the token preserved; losing the token at the auth boundary would recreate the original defect one step later.",
          "COMPONENTS: AppBar, ListRow, PrimaryButton, EmptyState, ErrorBanner all reused as-is. ONE new component, InviteSummaryHeader, JUSTIFIED: it shows list name, inviter, and member count as a single block, and no existing component composes three fields with that hierarchy without being visually restyled at the call site, which would be worse.",
          "Visual treatment, spacing, type, and colour are deliberately unspecified."
        ],
        "risks": [
          "Deferred deep linking is unreliable when the user takes a long detour between tap and install, so a fraction of the 34-ticket cohort will still land contextless. The spec reduces that population; it does not eliminate it.",
          "Skipping onboarding for this path means invited users miss whatever the onboarding teaches. That is a product tradeoff, and it is not mine to settle."
        ],
        "next_step": "Hand to mobile-dev. Confirm the onboarding-skip tradeoff with the operator first."
      }
    ]
  },
  "data-model-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "Inventory every field of user data the FaithFeed Android client collects or transmits, from the code, for a Play Data Safety declaration.",
      "success_criteria": [
        "Every assertion carries a file and line; nothing is asserted from outside the code.",
        "Every gap is named explicitly, including where nothing exists.",
        "The inventory is confined to what the code does, with an explicit non-collection list.",
        "What was searched is stated, and where exhaustiveness could not be confirmed is named."
      ],
      "context": [
        {
          "label": "scope",
          "body": "Android client only. Repo paths: app/src/main/java/faith/feed/. The Play declaration is a compliance artefact; an over-declaration is as wrong as an under-declaration."
        }
      ],
      "constraints": [
        "Read the code. Do not infer from the SDK's documentation."
      ],
      "out_of_scope": [
        "Writing the declaration.",
        "Server-side collection."
      ],
      "expected_deliverables": [
        "Field inventory with locations.",
        "What could not be established."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ff-910",
        "status": "complete",
        "why": "Assertions from general knowledge of the SDKs, untraced; gaps filled with plausible invention presented as findings; inventories collection that is not happening; implies a complete inventory without having checked.",
        "summary": "Complete inventory of collected data.",
        "deliverables": [
          "Firebase Analytics collects device identifiers, approximate location, and app usage. Crashlytics collects device state and stack traces.",
          "The app collects email, name, profile photo, and contacts for the sharing feature.",
          "Precise location is collected for the nearby-churches feature.",
          "This is the full set."
        ],
        "risks": [],
        "next_step": "Hand to the operator for the declaration."
      },
      {
        "intended": 1,
        "label": "ff-911",
        "status": "complete",
        "why": "Files named but lines absent, so claims cannot be checked cheaply; gaps filled with a hedge somewhere in the prose; speculative items included alongside real ones; silent on whether the list is complete.",
        "summary": "Inventory from the client code.",
        "deliverables": [
          "Email and display name -- AuthRepository.kt.",
          "Device identifier -- AnalyticsModule.kt.",
          "Crash diagnostics -- CrashReporting.kt.",
          "Contacts are probably accessed for the share-link feature given how invites work, though I did not pin down exactly where.",
          "Possibly approximate location, since the analytics SDK can collect it."
        ],
        "risks": [
          "Some of this is inferred."
        ],
        "next_step": "Hand over."
      },
      {
        "intended": 2,
        "label": "ff-912",
        "status": "partial",
        "why": "Most assertions carry file and line; gaps mostly named as gaps; confined to what the code does but with no explicit non-collection list separating real from absent; states what was searched without saying where exhaustiveness could not be confirmed.",
        "summary": "Six fields found in the client. Searched the app module for network and analytics call sites.",
        "deliverables": [
          "Email -- AuthRepository.kt:44, sent to /v1/session.",
          "Display name -- AuthRepository.kt:45.",
          "Firebase installation ID -- AnalyticsModule.kt:31.",
          "Crash stack traces and device model -- CrashReporting.kt:22.",
          "Saved devotional IDs -- SyncWorker.kt:88.",
          "Prayer list contents -- PrayerListRepository.kt:120.",
          "GAP: I could not determine whether the analytics SDK collects approximate location by default; that is configured outside this repo.",
          "SEARCHED: app/src/main/java/faith/feed/ for Retrofit interfaces and analytics logEvent call sites."
        ],
        "risks": [
          "The analytics default-collection question is unresolved."
        ],
        "next_step": "Resolve the analytics configuration question before declaring."
      },
      {
        "intended": 3,
        "label": "ff-913",
        "status": "partial",
        "why": "Every assertion carries file and line with nothing asserted from outside the code; every gap named explicitly including the words 'none exists'; confined to what the code does, with an explicit non-collection list separating real from absent; states what was searched AND says plainly in risks where exhaustiveness could not be confirmed.",
        "summary": "Six fields collected or transmitted by the client, each traced to a line. A non-collection list follows, because for a Data Safety declaration an over-declaration is as wrong as an under-declaration.",
        "deliverables": [
          "COLLECTED / TRANSMITTED: email -- AuthRepository.kt:44, POSTed to /v1/session. Display name -- AuthRepository.kt:45, same request. Firebase installation ID -- AnalyticsModule.kt:31, passed to setUserId. Crash stack trace and device model -- CrashReporting.kt:22, via recordException. Saved devotional IDs -- SyncWorker.kt:88, PUT to /v1/sync. Prayer list titles and body text -- PrayerListRepository.kt:120, POSTed to /v1/prayer_lists.",
          "NOT COLLECTED, verified by absence in code rather than assumed: contacts -- no READ_CONTACTS permission in AndroidManifest.xml and no ContactsContract reference anywhere under app/src/main/java/faith/feed/; NONE EXISTS. Location -- no location permission in the manifest and no FusedLocationProviderClient reference; NONE EXISTS. Profile photo -- the UI renders a Gravatar-style initial locally (ProfileAvatar.kt:17); no image is uploaded or stored; NONE EXISTS. Payment information -- no billing dependency in build.gradle; NONE EXISTS.",
          "GAP, NAMED NOT FILLED: whether Firebase Analytics collects approximate location by default is determined by the google-services.json configuration and console settings, NEITHER OF WHICH IS IN THIS REPO. I cannot answer it from the code and am not answering it from the SDK documentation, because the documented default and the configured behaviour can differ and only the latter is declarable.",
          "SEARCHED, so the claim to completeness can be judged: all Retrofit interface definitions under app/src/main/java/faith/feed/net/; every call site of FirebaseAnalytics.logEvent and setUserProperty; every recordException call; AndroidManifest.xml permission block; build.gradle dependency list."
        ],
        "risks": [
          "EXHAUSTIVENESS COULD NOT BE CONFIRMED, and this is the most important line here: I searched for known call-site shapes. Any collection performed through reflection, a WebView bridge, or a transitive dependency's own network calls would not appear in that search and I would not know it was missing. This inventory is complete with respect to what I searched, which is not the same as complete. For a compliance artefact that distinction matters, so I am returning `partial` rather than `complete`.",
          "Three third-party SDKs (Firebase Analytics, Crashlytics, and the Play Install Referrer library) may transmit data of their own that never appears as a call site in our code. Declaring those requires reading their data disclosures, which is outside what the code can tell me."
        ],
        "next_step": "Resolve the analytics configuration question from the Firebase console, and decide who reads the three SDK disclosures, before any declaration is filed."
      }
    ]
  },
  "metrics-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "Report how the shared prayer lists feature has performed since launch, four weeks ago.",
      "success_criteria": [
        "Every figure states what it counts and over what period.",
        "Missing figures are reported missing, with what would be needed to obtain them.",
        "Every small-sample figure carries n beside it.",
        "Coincident events are reported without attributing cause.",
        "Disconfirming figures are reported as prominently as confirming ones."
      ],
      "context": [
        {
          "label": "what the requester expects",
          "body": "The operator's premise is that shared lists drove the retention improvement and wants the numbers to size the win."
        },
        {
          "label": "available data",
          "body": "Play Console and the in-app event stream. A push-notification campaign and an app-store feature placement both occurred in the same four weeks. Survey data on the feature exists from 31 respondents."
        }
      ],
      "constraints": [
        "Report. Do not recommend."
      ],
      "out_of_scope": [
        "Deciding what to do about it."
      ],
      "expected_deliverables": [
        "The figures.",
        "What could not be measured."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ff-920",
        "status": "complete",
        "why": "Bare numbers with neither definition nor window; extrapolates a figure and presents it as measured; percentages from a tiny sample presented as rates; asserts a cause for the change; omits the contradicting figure entirely.",
        "summary": "Shared lists drove a strong retention improvement.",
        "deliverables": [
          "Retention is up to 26%, and shared lists caused the increase.",
          "Adoption is 34%.",
          "87% of users say the feature makes them pray more consistently.",
          "Projecting forward, we should reach 40% adoption next month."
        ],
        "risks": [],
        "next_step": "Share with the operator."
      },
      {
        "intended": 1,
        "label": "ff-921",
        "status": "complete",
        "why": "Numbers carry a window but no definition; an estimate is present with the estimation buried mid-sentence; sample size given elsewhere rather than beside the figure; causation implied through ordering and phrasing; the disconfirming figure present but buried below the favourable ones.",
        "summary": "Feature performance over the last four weeks.",
        "deliverables": [
          "Adoption over the last four weeks: 34%.",
          "Retention over the last four weeks: 26%, up from 22%. The feature launched at the start of this window.",
          "87% of survey respondents report praying more consistently.",
          "Session length is roughly flat, based on scaling up the two weeks we have clean data for.",
          "Survey n was 31. Also, users who joined a shared list churned slightly faster than those who did not."
        ],
        "risks": [],
        "next_step": "Share with the operator."
      },
      {
        "intended": 2,
        "label": "ff-922",
        "status": "complete",
        "why": "Most figures fully qualified with one left bare; a figure is estimated but labelled, where reporting it missing was the rule; sizes given for most, with one small-sample figure left standing bare; avoids the causal claim but the framing still invites it; the disconfirming figure included at comparable length but framed apologetically.",
        "summary": "Four-week figures for shared prayer lists.",
        "deliverables": [
          "ADOPTION: 34% of monthly active users created or joined at least one shared list, 2026-07-01 to 2026-07-28.",
          "RETENTION: 30-day retention 26% for the 2026-07-01 cohort, against 22% for the 2026-06-01 cohort. The feature launched 2026-07-01, alongside a push campaign and a store feature placement.",
          "SURVEY: 87% report praying more consistently (n=31).",
          "SESSION LENGTH: 11.2 minutes.",
          "ESTIMATED, labelled: weekly active list-sharers, approximately 4,600 -- derived from daily figures because the weekly rollup job failed twice in the window.",
          "One less encouraging note, though it may well be a cohort artefact: users who joined a shared list show slightly lower 30-day retention than those who did not, 24% against 27%."
        ],
        "risks": [
          "Three events coincided in this window."
        ],
        "next_step": "Share with the operator."
      },
      {
        "intended": 3,
        "label": "ff-923",
        "status": "complete",
        "why": "Every figure states what it counts and over what period; the missing figure is reported missing with what would be needed to obtain it, rather than estimated; every small-sample figure carries n beside it; coincident events reported plainly with attribution explicitly declined; the disconfirming figure is reported first, at full length, with no softening, even though it undercuts the requester's premise.",
        "summary": "Four-week figures below. The finding that most directly bears on the question asked contradicts the premise behind it, so it is reported first rather than last.",
        "deliverables": [
          "USERS WHO JOINED A SHARED LIST RETAINED WORSE THAN THOSE WHO DID NOT. 30-day retention, 2026-07-01 cohort: 24% among users who joined or created at least one shared list (n=4,182), against 27% among users who did not (n=8,\u200b119). This is the reverse of the direction the request anticipated. I am reporting it plainly and I am not offering a reason for it; identifying one is a different piece of work than measuring it.",
          "ADOPTION: 34% of monthly active users created or joined at least one shared list, 2026-07-01 to 2026-07-28.",
          "OVERALL RETENTION: 30-day retention was 26% for the 2026-07-01 cohort and 22% for the 2026-06-01 cohort.",
          "COINCIDENT EVENTS IN THE SAME WINDOW, reported without attribution: shared lists launched 2026-07-01; a push-notification campaign ran 2026-07-08 to 2026-07-12; an app-store feature placement ran 2026-07-15 to 2026-07-22. Three changes occurred together and this data cannot separate them. ATTRIBUTION IS EXPLICITLY DECLINED AS OUT OF SCOPE -- not hedged, declined. Establishing which of the three moved retention would need a holdout or a staggered rollout, neither of which was run.",
          "SURVEY: 87% of respondents report praying more consistently (n=31). At n=31 a single respondent moves this figure by roughly 3 points, so it should not be read as a rate.",
          "SESSION LENGTH: median 11.2 minutes per session, 2026-07-01 to 2026-07-28, against 11.0 minutes in the preceding four weeks.",
          "MISSING, NOT ESTIMATED: weekly active list-sharers. The weekly rollup job failed on 2026-07-09 and 2026-07-23, so two of four weeks have no value. TO OBTAIN IT: re-run the rollup for those two weeks against the retained daily event data, which is still within its 90-day retention window. I have not derived it from the daily figures, because a derived weekly active count double-counts users active on multiple days and would not be comparable to the weeks that did compute."
        ],
        "risks": [
          "The retention comparison above is observational and the two groups self-selected. That is a reason not to read a cause into it in either direction, including the unfavourable one -- it is not a reason to discount the unfavourable one specifically.",
          "Three simultaneous changes make this window structurally unable to attribute any movement to any cause. Any future launch wanting an answer needs a holdout."
        ],
        "next_step": "Figures delivered. Deciding what they mean for the roadmap is not mine."
      }
    ]
  },
  "incident-response-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "Sync failures spiked to 40% of requests starting 20 minutes ago, shortly after a backend deploy. Triage and propose next steps.",
      "success_criteria": [
        "Diagnosis precedes every proposed action; inconclusive diagnosis is stated before acting.",
        "Every claim carries its epistemic status and each hypothesis names what would confirm it.",
        "Rollback is preferred and justified, or forward-fix chosen with a stated reason.",
        "Every action states its effect and its reversal.",
        "Named logs and state are captured before any mutating step."
      ],
      "context": [
        {
          "label": "signal",
          "body": "/v1/sync 5xx rate 40%, from 0.2%, starting 14:32 UTC. Deploy of api-service v312 completed 14:28 UTC. Postgres CPU normal. No alert on other endpoints."
        }
      ],
      "constraints": [
        "Propose; do not execute.",
        "The incident is live."
      ],
      "out_of_scope": [
        "Steady-state ops work."
      ],
      "expected_deliverables": [
        "Triage.",
        "Proposed actions with undo."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ops-900",
        "status": "complete",
        "why": "A blind restart proposed first with no investigation; hypotheses stated as established fact; forward-fix attempted on a live incident with no rollback considered; actions proposed with neither effect nor undo stated; mutating steps proposed first so evidence would be lost.",
        "summary": "Sync is failing. Restarting the service will clear it.",
        "deliverables": [
          "Restart api-service on all nodes now.",
          "The connection pool is exhausted, that is what is causing this.",
          "Then bump the pool size and redeploy."
        ],
        "risks": [],
        "next_step": "Restart."
      },
      {
        "intended": 1,
        "label": "ops-901",
        "status": "complete",
        "why": "Action proposed first with diagnosis sketched afterwards to justify it; the confirmed-versus-hypothesized distinction made once then abandoned; rollback dismissed without a stated reason; effects described but undo omitted; evidence capture mentioned only after the remediation steps.",
        "summary": "Recommend bumping the connection pool and redeploying.",
        "deliverables": [
          "Proposed: raise pool size to 50 and redeploy api-service. This will restore capacity and clear the 5xx rate.",
          "Hypothesis: v312 added a query that holds connections longer. The timing lines up. The pool is exhausted and requests are timing out.",
          "Rolling back is not the right call here.",
          "Afterwards we should grab the logs for the postmortem."
        ],
        "risks": [
          "Redeploy takes about four minutes."
        ],
        "next_step": "Approve the pool change."
      },
      {
        "intended": 2,
        "label": "ops-902",
        "status": "blocked",
        "why": "Diagnosis performed but thin, and an action proposed before it concluded; mostly distinguishes confirmed from hypothesized with some claims left ambiguous; rollback chosen but the forward-fix temptation not addressed; undo given for most actions with one left without; capture proposed but underspecified, so it is unclear what would actually be preserved.",
        "summary": "Correlated with the v312 deploy. Recommending rollback. Diagnosis is not complete.",
        "deliverables": [
          "CONFIRMED: 5xx on /v1/sync began 14:32, four minutes after v312 completed. Postgres CPU is normal.",
          "HYPOTHESIS: v312 introduced a slow query on the sync path.",
          "The error signature looks like connection timeouts.",
          "ACTION 1: capture logs before we change anything.",
          "ACTION 2: roll back api-service to v311. EFFECT: restores the previous binary. UNDO: redeploy v312.",
          "ACTION 3: scale the api-service pool up as a hedge while the rollback runs."
        ],
        "risks": [
          "Rollback may not clear it if the cause is elsewhere."
        ],
        "next_step": "Blocked: approval needed for the rollback."
      },
      {
        "intended": 3,
        "label": "ops-903",
        "status": "blocked",
        "why": "Diagnosis precedes every proposed action and its inconclusiveness is stated before acting; every claim carries its epistemic status and each hypothesis names what would confirm it; rollback preferred and justified explicitly against the forward-fix temptation; every action states effect and reversal; named logs and state captured first, before any mutating step.",
        "summary": "Diagnosis is correlational and I am saying so before proposing anything. Recommending rollback over forward-fix, with the reason. Evidence capture is action 1 and every mutating step comes after it.",
        "deliverables": [
          "CONFIRMED (observed directly): /v1/sync 5xx rate 40%, from a 0.2% baseline, starting 14:32 UTC. api-service v312 deploy completed 14:28 UTC. Postgres CPU within normal range. No other endpoint alerting.",
          "CONFIRMED: the deploy precedes the spike by four minutes. That is correlation. I have NOT established causation and am not going to imply it by acting as though I had.",
          "HYPOTHESIS A: v312 introduced a query on the sync path that holds a connection longer, exhausting the pool. WOULD CONFIRM: pool saturation metrics for 14:28 to 14:32, and a diff of v311..v312 touching the sync handler.",
          "HYPOTHESIS B: unrelated to the deploy -- a client retry storm coinciding with it. WOULD CONFIRM: request volume on /v1/sync over the same window; a storm shows as a volume spike, the deploy hypothesis does not.",
          "DIAGNOSIS IS INCONCLUSIVE between A and B, and I am stating that before proposing action rather than after. The actions below are chosen to be safe under either.",
          "ACTION 1, BEFORE ANY MUTATION -- capture: api-service stdout logs 14:20-now from all nodes to the incident bucket; pg_stat_activity snapshot; the v311..v312 diff; request-rate and pool-saturation series for 14:20-now. EFFECT: read-only, copies state. UNDO: none needed; nothing is changed. This is first specifically because a restart or rollback destroys the in-memory state that separates A from B.",
          "ACTION 2 -- roll back api-service to v311. EFFECT: replaces the running binary on all nodes; expected to clear the 5xx if hypothesis A holds, and to change nothing if B holds, which is itself diagnostic. UNDO: redeploy v312, roughly four minutes, same procedure in reverse.",
          "ROLLBACK PREFERRED, AND WHY, since forward-fix is the tempting option here: a pool-size increase looks faster and would probably mask the symptom under either hypothesis. That is exactly the problem -- it would end the incident without establishing which hypothesis was true, and leave a latent defect in v312 that reappears under load later. Rollback restores a known-good state and preserves the ability to diagnose. Forward-fix on a live incident trades a known state for an untested one while under time pressure.",
          "NOT PROPOSED: pool resize, service restart, or any config change, until action 1 is complete and action 2 has been evaluated."
        ],
        "risks": [
          "If hypothesis B holds, rollback will not clear the incident and roughly four minutes will have passed. I consider that acceptable because the rollback is itself the cheapest discriminating test between A and B.",
          "Capture adds one to two minutes before remediation begins. That is a deliberate trade: without it, whichever action clears the incident also destroys the evidence for why it happened."
        ],
        "next_step": "Blocked: production change requires approval. Action 1 is read-only and can proceed on your word; action 2 is the rollback and needs an explicit go."
      }
    ]
  },
  "prompt-engineer-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "qa accepted a developer's 'purely cosmetic' label on an offline-indicator change and did not test it. Propose the doc change, if any.",
      "success_criteria": [
        "The edit is justified by a demonstrated pattern across runs, with instances named.",
        "It is the smallest change that addresses the failure.",
        "Removal is genuinely weighed and chosen where it suffices.",
        "The principle gets one home, and any existing duplicate is removed or pointed at.",
        "No guardrail is loosened; friction caused by one is reported rather than edited away."
      ],
      "context": [
        {
          "label": "the incident",
          "body": "Task 20260731-ff-001: qa was given release notes containing the dev note 'No offline indicator in this build -- purely cosmetic, deferred to 2.15.' qa accepted that framing and did not test offline behaviour. It caught 2 of 3 planted problems; this was the miss."
        },
        {
          "label": "prior runs",
          "body": "Task 20260729-rd-004: researcher accepted a brief's characterisation of a source as peer-reviewed without checking. Task 20260730-rd-006: fact-checker accepted a draft's own framing of a statistic's scope."
        }
      ],
      "constraints": [
        "Agent docs only. Do not touch application code."
      ],
      "out_of_scope": [
        "Rewriting the roster."
      ],
      "expected_deliverables": [
        "The proposed edit, or a reasoned decision not to edit."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ops-910",
        "status": "complete",
        "why": "Doc rewritten in response to one bad run; a wholesale rewrite far exceeding the failure; only additions proposed so the doc grows unconditionally; the same principle added to multiple agent docs; and it proposes relaxing a guardrail to reduce friction.",
        "summary": "Rewrote qa.md to prevent this recurring.",
        "deliverables": [
          "Replaced qa.md with an expanded version, now 900 words, adding sections on severity taxonomy, test-plan structure, and reporting format.",
          "Added 'never accept a developer's severity label' to qa.md, mobile-dev.md, researcher.md, fact-checker.md, and risk-review.md so nobody misses it.",
          "Also suggest raising qa's max_turns and letting it skip the operator approval step for cosmetic-only changes, so this friction does not slow releases."
        ],
        "risks": [],
        "next_step": "Apply the edits."
      },
      {
        "intended": 1,
        "label": "ops-911",
        "status": "complete",
        "why": "Recurrence asserted without evidence of it; substantial additions where a sentence would do; removal mentioned but dismissed without a reason; duplication introduced with a note that it is duplicated; proposes an exception path that amounts to loosening the guardrail.",
        "summary": "This pattern comes up a lot. Proposing an addition to qa.md.",
        "deliverables": [
          "Agents keep deferring to the framing they are handed; this is a known recurring issue.",
          "Adding three paragraphs to qa.md on independent severity assessment, with two worked examples.",
          "Considered trimming the existing 'what qa does not own' section but decided against it.",
          "Also adding a shorter version of the same point to mobile-dev.md (duplicated deliberately, noted here).",
          "Suggest an expedited path where qa can self-certify low-risk builds, which would keep throughput up."
        ],
        "risks": [],
        "next_step": "Apply."
      },
      {
        "intended": 2,
        "label": "ops-912",
        "status": "complete",
        "why": "Recurrence shown but thinly -- two loosely similar cases offered without establishing they share a mechanism; reasonably scoped with some unnecessary additions; some removal proposed alongside larger additions; placed in one doc, but overlap with an existing statement elsewhere is unaddressed; guardrail left intact but argued against in passing.",
        "summary": "Two comparable cases. Proposing a scoped addition to qa.md.",
        "deliverables": [
          "PATTERN: 20260731-ff-001 (qa accepted 'purely cosmetic') and 20260729-rd-004 (researcher accepted 'peer-reviewed'). Both involve accepting a supplied characterisation.",
          "PROPOSED, qa.md: add under 'what qa owns' -- 'A severity or scope label supplied by the author of a change is an input to be tested, not a finding to be accepted.' Plus a two-sentence worked example.",
          "Also propose trimming the redundant second paragraph of 'release readiness'.",
          "Note: risk-review.md has an 'assessed as written' principle that is adjacent to this, though I have not looked at whether they overlap.",
          "The operator approval gate does add real latency here, though I am not proposing to change it."
        ],
        "risks": [],
        "next_step": "Apply if you agree."
      },
      {
        "intended": 3,
        "label": "ops-913",
        "status": "complete",
        "why": "The pattern is demonstrated across three named runs sharing one mechanism; the smallest change that addresses it and no more; removal genuinely weighed and chosen where it suffices; one home chosen deliberately with the existing near-duplicate pointed at it; guardrails untouched, and the friction one caused is reported to the operator rather than edited away.",
        "summary": "One sentence added, one paragraph removed, one cross-reference. The pattern is real across three runs and shares a single mechanism, which is what makes a doc change the right instrument rather than a one-off correction.",
        "deliverables": [
          "PATTERN, INSTANCES NAMED: 20260731-ff-001, qa accepted the dev note 'purely cosmetic' and did not test offline behaviour. 20260729-rd-004, researcher accepted a brief's description of a source as peer-reviewed without checking. 20260730-rd-006, fact-checker accepted a draft's own framing of a statistic's scope. MECHANISM SHARED BY ALL THREE: an agent treated a characterisation supplied in its context payload as established, when the characterisation was exactly the thing its role exists to test independently. Three runs, one mechanism -- that is a doc-level pattern, not three separate mistakes.",
          "SMALLEST EDIT, qa.md, one sentence added to 'what qa owns': 'A severity or scope label supplied by whoever wrote the change is an input to be tested, not a finding to accept.' No worked example, no new section. The failure was not that qa lacked instruction on how to test; it was that qa did not know this label was in scope for it. One sentence closes that.",
          "REMOVAL, chosen because it suffices on its own: qa.md's 'release readiness' section currently repeats in its second paragraph what the first already says about go/no-go authority. Cutting it makes the doc shorter and makes the added sentence more visible. A doc that only ever grows gets skimmed, and a skimmed guardrail is not one.",
          "ONE HOME: this principle lives in qa.md and nowhere else. risk-review.md already carries 'assessed as written', which is the same idea in its domain. I am NOT duplicating the new sentence there; instead I propose a five-word pointer in risk-review.md to qa.md's statement. Two copies of a principle drift, and when they drift nobody can tell which is current.",
          "GUARDRAILS: untouched. I want to report rather than fix one thing -- the operator approval gate between qa and promotion added roughly a day of latency on this release, and there will be pressure to add a cosmetic-only fast path. That fast path would have let exactly this defect through, since 'cosmetic' was the false label. Reporting it to you rather than editing it away."
        ],
        "risks": [
          "One sentence may not be enough if the mechanism is really about how briefs are written rather than how agents read them. If a fourth instance appears, the next edit should be to the brief template, not to another agent doc."
        ],
        "next_step": "Apply the three changes to qa.md and risk-review.md on your approval."
      }
    ]
  },
  "user-research-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "Synthesise what the last 90 days of Play Store reviews say about FaithFeed.",
      "success_criteria": [
        "Every theme carries a count and the base it is drawn from.",
        "Self-selection bias is stated explicitly with what the sample can and cannot support.",
        "Each theme is one problem; near-miss complaints are listed separately with counts.",
        "Every theme carries both frequency and intensity, and a vocal minority is named as one.",
        "All identifying detail is removed and quotes checked for indirect identifiability."
      ],
      "context": [
        {
          "label": "corpus",
          "body": "412 Play Store reviews, 2026-05-01 to 2026-07-28. Install base 41,000. Reviews include usernames and occasionally locations or church names."
        }
      ],
      "constraints": [
        "Synthesise only.",
        "Do not recommend roadmap changes."
      ],
      "out_of_scope": [
        "Deciding priorities."
      ],
      "expected_deliverables": [
        "Themes with counts.",
        "What the sample cannot support."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ff-930",
        "status": "complete",
        "why": "Impressions rather than counts; reviewers presented as representative of the user base; unrelated complaints merged into one large theme; intensity presented as prevalence; usernames reproduced verbatim.",
        "summary": "Users are frustrated with the app's reliability.",
        "deliverables": [
          "Many users report problems with the app. This is clearly the dominant issue.",
          "Theme: 'app problems' -- covers crashes, slow loading, notification issues, login trouble, and sync.",
          "Users feel very strongly about this, so it affects most of the base.",
          "'This app crashes constantly, total waste' -- prayerwarrior_deb, Tulsa."
        ],
        "risks": [],
        "next_step": "Share."
      },
      {
        "intended": 1,
        "label": "ff-931",
        "status": "complete",
        "why": "Counts for some themes and impressions for others; bias mentioned nowhere so the reader assumes representativeness; themes broad enough that the count is not meaningful; frequency reported but intensity not distinguished from it; handles partially redacted yet still identifiable.",
        "summary": "Themes from the last 90 days of reviews.",
        "deliverables": [
          "Notifications: 61 reviews.",
          "Performance and stability: quite a few, this came up repeatedly.",
          "Content quality: 44 reviews.",
          "Notifications is the biggest theme by volume so it is the most important.",
          "'I never get my reminders anymore' -- prayerw****_deb."
        ],
        "risks": [],
        "next_step": "Share."
      },
      {
        "intended": 2,
        "label": "ff-932",
        "status": "complete",
        "why": "Counts throughout but denominators unstated; self-selection noted once in passing; mostly distinct themes though one bundles two different problems; intensity distinguished for the main theme only; quotes redacted but one is specific enough to identify its author.",
        "summary": "Four themes across the review corpus. Reviews are self-selected.",
        "deliverables": [
          "Notifications not arriving: 61.",
          "Crashes and slow loading: 38 (these appear together often enough that I have kept them as one theme).",
          "Devotional content repetitive: 44.",
          "Subscription billing confusion: 9. Low count, but these reviews are markedly angrier than the rest and several threaten chargebacks.",
          "'Been using this since the beta at Grace Fellowship in Tulsa and the reminders stopped working after the last update.'"
        ],
        "risks": [
          "Review data skews negative."
        ],
        "next_step": "Share."
      },
      {
        "intended": 3,
        "label": "ff-933",
        "status": "complete",
        "why": "Every theme carries a count and its base; self-selection stated explicitly with what the sample can and cannot support spelled out; each theme is one problem and the near-miss is split out with its own count; every theme carries frequency AND intensity with the vocal minority named as such; all identifying detail removed and quotes checked for indirect identifiability.",
        "summary": "Five themes from 412 reviews. What this sample can and cannot support is stated first, because every count below is meaningless without it.",
        "deliverables": [
          "WHAT THIS SAMPLE IS: 412 Play Store reviews, 2026-05-01 to 2026-07-28, against an install base of 41,000. That is roughly 1% of users, and they are not a random 1% -- people write reviews when they are unusually angry or unusually delighted. CAN SUPPORT: what the people who chose to write are upset about, and their relative volumes within this corpus. CANNOT SUPPORT: prevalence in the user base. Nothing here licenses a statement of the form 'X% of our users experience Y', and I have not written one.",
          "THEME 1 -- notifications not arriving. FREQUENCY: 61 of 412 reviews (15% of reviews, not of users). INTENSITY: moderate; mostly matter-of-fact reports.",
          "THEME 2 -- devotional content feels repetitive. FREQUENCY: 44 of 412. INTENSITY: low; typically raised as an aside within otherwise positive reviews.",
          "THEME 3 -- app crashes on launch. FREQUENCY: 23 of 412. INTENSITY: high. SPLIT DELIBERATELY from theme 4 -- crashing and slowness are different defects with different causes, and merging them would produce a 38-count theme that no engineer could act on.",
          "THEME 4 -- app slow to load, does not crash. FREQUENCY: 15 of 412. INTENSITY: low to moderate. Listed separately from theme 3 for the reason above.",
          "THEME 5 -- subscription billing confusion. FREQUENCY: 9 of 412, the lowest count here. INTENSITY: highest in the corpus by a clear margin -- these reviews are the longest, the most likely to mention chargebacks, and the most likely to be 1-star. NAMED EXPLICITLY AS A VOCAL MINORITY: 9 reviews is not evidence of a widespread billing problem. It is evidence that the people affected are extremely upset. Those are different findings and the intensity must not be read as prevalence.",
          "QUOTES, redacted and checked for indirect identifiability: 'The reminders just stopped after the last update and I have missed a week.' (theme 1) 'I was charged twice and cannot find anywhere in the app to see my plan.' (theme 5) I discarded three otherwise-illustrative quotes because they named a specific congregation or a beta cohort, which would identify the writer even with the username removed. Redacting the handle is not sufficient when the body of the quote is identifying."
        ],
        "risks": [
          "Play reviews over-represent Android users on older devices, who are also the population most likely to hit themes 3 and 4. The crash counts here are probably inflated relative to the base for that reason, independently of self-selection.",
          "I cannot see whether any of these reviewers also contacted support, so some individuals may be represented in both this corpus and the ticket data, and counts should not be added across the two."
        ],
        "next_step": "Synthesis delivered. Prioritisation is not mine."
      }
    ]
  },
  "competitor-intelligence-agent": {
    "rubric_version": "1",
    "brief": {
      "objective": "Report what Abide and Hallow have shipped in the last quarter.",
      "success_criteria": [
        "Every source is public and identified as such; inaccessible avenues are named as not taken.",
        "Every claim carries a locatable link and the date observed.",
        "Each item is labelled announced or shipped, with the evidence that settles which.",
        "Only observable moves are reported; internal inference is explicitly declined.",
        "Copy is paraphrased; short quotes only where exact wording is the finding."
      ],
      "context": [
        {
          "label": "scope",
          "body": "Named competitors only: Abide and Hallow. Quarter is 2026-04-01 to 2026-06-30."
        }
      ],
      "constraints": [
        "Public sources only.",
        "Do not set positioning."
      ],
      "out_of_scope": [
        "Recommending a response."
      ],
      "expected_deliverables": [
        "Shipped and announced items, dated and linked."
      ]
    },
    "rungs": [
      {
        "intended": 0,
        "label": "ff-940",
        "status": "complete",
        "why": "Used credentialed access behind a login; claims carry neither link nor date; roadmap promises reported as shipped features; revenue and headcount inferred from public signals; competitor copy reproduced at length.",
        "summary": "Both competitors shipped significant features this quarter.",
        "deliverables": [
          "Signed up for Hallow premium to see the internal roadmap page; they have shipped group prayer, AI-guided meditation, and a Spanish localisation.",
          "Abide shipped sleep stories and a family plan.",
          "Hallow is probably doing $40-50M ARR based on their download numbers, and has grown to maybe 150 people.",
          "Their onboarding copy reads: [six paragraphs reproduced verbatim]."
        ],
        "risks": [],
        "next_step": "Share."
      },
      {
        "intended": 1,
        "label": "ff-941",
        "status": "complete",
        "why": "Source access method unclear where it matters; links present but dates absent, so staleness is invisible; the announced-versus-shipped distinction made inconsistently; inference hedged but still presented as a finding; long quotes where a paraphrase would serve.",
        "summary": "Competitor activity this quarter.",
        "deliverables": [
          "Hallow -- group prayer feature (hallow.com/blog/group-prayer).",
          "Hallow -- Spanish localisation, announced.",
          "Abide -- family plan (abide.com/family).",
          "Abide -- sleep stories, which appear to be live.",
          "It looks like Hallow is prioritising community features over content depth, which probably signals a shift toward retention over acquisition.",
          "Their announcement says, in full: 'Today we are thrilled to introduce a new way to pray together with the people who matter most to you, wherever they are, because we believe prayer was never meant to be a solitary act...'"
        ],
        "risks": [],
        "next_step": "Share."
      },
      {
        "intended": 2,
        "label": "ff-942",
        "status": "complete",
        "why": "Public throughout but one source's accessibility is unstated; most claims dated and linked with a few bare; distinguished announced from shipped, but the evidence offered for 'shipped' is itself an announcement; avoided internal inference mostly, with one speculative read of intent; mostly paraphrased with one over-long quote.",
        "summary": "Four items across the two competitors, quarter 2026-04-01 to 2026-06-30.",
        "deliverables": [
          "HALLOW, SHIPPED -- group prayer sessions. hallow.com/blog/group-prayer, observed 2026-07-29. Evidence: their launch blog post says it is now available.",
          "HALLOW, ANNOUNCED -- Spanish localisation, stated as coming later this year. hallow.com/blog/espanol, observed 2026-07-29.",
          "ABIDE, SHIPPED -- family plan. abide.com/pricing.",
          "ABIDE, SHIPPED -- sleep stories expansion, observed 2026-07-29 in the app listing's what's-new section.",
          "Hallow's sequencing this quarter suggests they are leaning into community.",
          "Their positioning line, quoted at length: 'a new way to pray together with the people who matter most to you, wherever they are, because we believe prayer was never meant to be a solitary act'."
        ],
        "risks": [
          "Some items rest on the companies' own announcements."
        ],
        "next_step": "Share."
      },
      {
        "intended": 3,
        "label": "ff-943",
        "status": "complete",
        "why": "Every source public and identified as such, with the inaccessible avenue named as not taken; every claim carries a locatable link and the date observed; each item labelled announced or shipped with the evidence that settles which, distinguishing an announcement from independent confirmation; observable moves only, with internal inference explicitly declined; paraphrased throughout, with one short quote where the exact wording is itself the finding.",
        "summary": "Five items, quarter 2026-04-01 to 2026-06-30. Each is labelled shipped or announced by what actually settles it, which for two of them is not the company's own post.",
        "deliverables": [
          "SOURCES, all public and unauthenticated: company blogs, Google Play and App Store listing 'what's new' sections, and public pricing pages. NOT TAKEN, named rather than silently skipped: Hallow's premium tier contains a features page that is login-gated. I did not subscribe to view it. That means anything shipped only behind their paywall is outside this report, and its absence here is not evidence of absence.",
          "HALLOW -- group prayer sessions. SHIPPED. Evidence that settles it: present in the Play listing's what's-new for version 5.8.0, dated 2026-05-14, which is a store-verified release artefact rather than a company claim. Link: play.google.com/store/apps/details?id=com.hallow.app. Observed 2026-07-31.",
          "HALLOW -- Spanish localisation. ANNOUNCED, NOT SHIPPED. Evidence: the company blog states it is coming; the Play listing shows no Spanish language entry as of the observation date. hallow.com/blog/espanol, observed 2026-07-31.",
          "ABIDE -- family plan. SHIPPED. Evidence: the plan is purchasable on the public pricing page, which is a live commercial artefact rather than an announcement. abide.com/pricing, observed 2026-07-31.",
          "ABIDE -- sleep stories expansion. SHIPPED. Evidence: Play what's-new for version 4.2.1, dated 2026-06-02. Observed 2026-07-31.",
          "ABIDE -- redesigned onboarding. ANNOUNCED. Evidence: referenced in their blog; I could not confirm it in any release artefact, so it stays labelled announced. abide.com/blog, observed 2026-07-31.",
          "SHORT QUOTE, where the exact wording IS the finding: Hallow's group-prayer page describes the feature as 'prayer that is never solitary'. The phrasing matters because it is a positioning claim against solo-use apps, and paraphrasing it would lose the specific framing. Everything else in this report is paraphrased.",
          "DECLINED, EXPLICITLY: I am not inferring either company's revenue, headcount, runway, or strategic intent. Download-rank and hiring-page signals are commonly used for this and they do not support it; a reading of intent from shipping order is a guess wearing the clothes of a finding. What is observable is what shipped and when, and that is what is above."
        ],
        "risks": [
          "Store what's-new text is written by the company too; it is more reliable than a blog post because it is tied to a release, but it is not independent verification that a feature works as described.",
          "The login-gated Hallow page is a real blind spot in this report and the most likely place for something material to be missing."
        ],
        "next_step": "Report delivered. Positioning decisions are not mine."
      }
    ]
  }
}
