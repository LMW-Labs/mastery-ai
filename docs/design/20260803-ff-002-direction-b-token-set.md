# FaithFeed Direction B — the accepted token set

Accepted output of `20260803-ff-002` (`visual-design`), verdict `accept` at 2026-08-04 07:46 CDT, run `f96659c2f06c`.

Verbatim transcription of the accepted return. This is the document that decides *why Direction B*; its sibling `20260803-ff-003-theme-migration-plan.md` decides how the legacy constants map onto it and was explicitly forbidden from revisiting anything settled here.

## Deliverables returned

- Direction B dark-only token set (colour, radius, spacing, motion, glass, elevation)
- Gold ramp derived from #C4A24A (gold-deep, gold, gold-bright, gold-pale), each step measured against all 4 surfaces
- Functional blue #64AEED, named and measured against all 4 surfaces
- Full contrast table: every foreground token × all 4 surfaces, AAA/AA/AA-large/FAIL labels, restrictions on every FAIL and AA-large pair
- Warning-hue collision resolved: hue moved (new-warning #FA7223), cost stated, plus the unflagged #FBBF24/gold near-collision caught and resolved, holyGold/highlightYellow/Ember dispositions given
- Gold-derived replacements for voided primary, accent, glow (e2/e3), and gradient (Halo Gold) tokens, each measured
- Font specification: Sora, weights 400/500/600/700, local-bundle recommendation with reason grounded in repo's actual google_fonts non-usage
- main.dart dependency named for dark-only (theme: AppTheme.darkTheme at line 116, builder Container at line 119, retirement of AppTheme.lightTheme)

## Specification

```text
DIRECTION B TOKEN SET — DARK-ONLY, ANCHORED ON #C4A24A. Verified against lib/theme/app_theme.dart and pubspec.yaml directly (not the survey) where noted.

=== 0. DARK-ONLY STATEMENT & main.dart DEPENDENCY (repo-verified) ===
Spec is dark-only: gold fails on both light surfaces measured (#FFFFFF 2.44, #F5F3EF 2.20), so no light companion exists in this direction.
DISCREPANCY FLAG: the brief's framing assumes dark is the operative theme needing extension. The repo says otherwise: app_theme.dart labels its own dark block 'DARK THEME COLORS (Legacy — Keeping for reference)' (line 36) while the light block is headed 'LIGHT THEME COLORS (Glassmorphism Premium Design)' (line 7), and main.dart:116 sets `theme: AppTheme.lightTheme` — there is no `darkTheme:` or `themeMode:` param at all. Today the app actively runs light theme; dark is the vestigial one. Dark-only therefore requires, concretely: (1) main.dart:116 `theme: AppTheme.lightTheme` → `theme: AppTheme.darkTheme` (rebuilt from this token set) as MaterialApp's only theme argument — no `darkTheme:`/`themeMode:` added, since a mode switch reintroduces exactly the light companion this direction rejects; (2) main.dart:119, the app-wide `builder` Container currently `color: AppTheme.lightBackground`, must become the new canvas token (#0B0E14) or every screen paints dark content over a light root background; (3) the entire 'LIGHT THEME' constant block and `AppTheme.lightTheme` should be retired outright, not left dormant, since an unused light path is how it gets silently reactivated later.

=== 1. SURFACES (carried forward, re-verified by luminance calc) ===
canvas #0B0E14 (L=0.00435) | surface #12161F (L=0.00802) | surface-elevated #1A2030 (L=0.01466) | surface-highlight #232B40 (L=0.02455). My luminance math reproduces the operator's given gold ratios exactly (7.92/7.42/6.66/5.78), confirming the method used throughout.

=== 2. GOLD RAMP (derived from #C4A24A, HSL 43.3°/50.8%/52.9%, lightness-only steps, each measured individually) ===
- gold-deep #836A2B (L≈0.34): canvas 3.74 AA-large | surface 3.50 AA-large | surface-elevated 3.14 AA-large | surface-highlight 2.72 FAIL. RESTRICTION: never as body-text foreground anywhere; on surface-highlight it fails outright even for large text — do not use there as foreground. Its designed role is a fill (see §6), not text.
- gold (base) #C4A24A — operator value, unchanged: canvas 7.92 AAA | surface 7.42 AAA | surface-elevated 6.66 AA | surface-highlight 5.78 AA. No FAIL; AAA only on the two darkest surfaces.
- gold-bright #D2B875 (L≈0.4927): canvas 9.99 AAA | surface 9.35 AAA | surface-elevated 8.39 AAA | surface-highlight 7.28 AAA. Clean AAA on all four — the safe gold for small text/icons anywhere.
- gold-pale #E1D0A3 (L≈0.6374): canvas 12.65 AAA | surface 11.85 AAA | surface-elevated 10.63 AAA | surface-highlight 9.22 AAA. Highest-margin gold; reads closer to cream — reserve for cases needing maximum headroom, not default brand color.
No step inherits another's ratio; each was computed from its own hex.

=== 3. FUNCTIONAL BLUE ===
functional-blue = #64AEED (identical hex to legacy lightBlue/primaryTeal — kept deliberately, not because it must stay but because it already clears AA everywhere and lets the 930-site primaryTeal migration in ff-003 be a rename rather than a recolor, which is the exact cost argument the palette policy states). Measured: canvas 8.11 AAA | surface 7.60 AAA | surface-elevated 6.82 AA | surface-highlight 5.91 AA. No FAIL.

=== 4. FULL CONTRAST TABLE (every foreground token × 4 surfaces) ===
on-surface #F4F6FB: 17.87/16.74/15.01/13.02 — AAA all four.
on-surface-variant #A9B2C6: 9.09 AAA / 8.52 AAA / 7.64 AAA / 6.62 AA.
on-surface-muted #6E7893: 4.40 / 4.12 / 3.69 / 3.21 — AA-large only on all four (all fail the 4.5 normal-text floor, all clear the 3.0 large-text floor). RESTRICTION: never for normal-weight body text on any surface, at any size below large-text thresholds (≥18px regular / ≥14px bold); on surface-highlight (3.21) it is barely above the 3.0 floor — treat as avoid-in-practice there, canvas/surface only.
gold ramp (4 steps): see §2.
functional-blue: see §3.
success #34D399: 10.05/9.41/8.45/7.33 — AAA all four.
error #F87171: 6.98/6.54/5.87/5.09 — AA all four (none reach 7.0).
new-warning #FA7223 (replaces warningAmber/the colliding 'warning' value — see §5): 6.90/6.46/5.80/5.03 — AA all four, no FAIL.
brand-accent (=gold-bright): AAA all four, see §2.
on-brand-primary-ink #0B0E14 atop brand-primary fill (gold base): 7.92 AAA — defined only for text/icons on top of the gold fill, not as a general foreground against the four neutral surfaces (it would be near-invisible there; that pairing is undefined/prohibited).
on-brand-primary-pressed-ink: on-surface #F4F6FB atop brand-primary-pressed fill (gold-deep): 4.79 AA.

=== 5. WARNING-HUE COLLISION — RESOLVED, NOT NOTED ===
Additional discrepancy the brief's own collision analysis missed: the carried-forward semantic 'warning' value #FBBF24 (given as 'all AAA') computes to hue 43.26° — essentially identical to gold's 43.3°, a near-total collision, worse than the two the brief names (warningAmber #F59E0B at 5.6° away, highlightYellow #F5EB30 at 13.7° away). Carrying #FBBF24 forward unchanged into a gold-anchored system was not viable despite being labeled 'carried forward'; flagging it here per the instruction to say so when repo reality and brief framing disagree.
CHOICE: move the warning hue, not restrict gold. Restricting gold's surface co-occurrence was rejected because gold must appear broadly across brand CTAs, premium badges and selected states per the palette policy — narrowing its placement to dodge a functional status color would cost more product surface than moving one semantic hue.
NEW WARNING = #FA7223 (HSL 22°/96%/56%), 21.3° from gold's 43.3° and 22° from error's 0° hue — clear separation from both neighbors. Measured in §4: AA on all four surfaces, no FAIL.
COST: (a) the new warning is AA, not AAA, on every surface — the old #FBBF24 was brighter/AAA but only because it borrowed gold's own hue-brightness signature, which is precisely the problem; (b) holyGold (app_theme.dart:77, alias of highlightYellow #F5EB30) is retired as a distinct hue — its name already claims to be gold, so its identity folds into the gold token/ramp rather than remaining bright yellow; call sites currently rendering holyGold will visibly shift from yellow to gold (disposition only — the call-site mapping is 20260803-ff-003's). (c) highlightYellow itself has no remaining role in Direction B (retired as a unique hue: brand-moment uses move to gold, warning-moment uses move to new-warning) — also a disposition, not a mapping. (d) 'Ember' (#FB7185→#FBBF24) — brief left this as a keep-or-retire call on its own (non-blue) merits: RETIRE. Its end stop is exactly the hue we just moved off of; a gradient sweeping through gold's exact hue reintroduces the misread the whole resolution exists to prevent.

=== 6. GOLD-DERIVED REPLACEMENTS FOR VOIDED PRIMARY / ACCENT / GLOW / GRADIENT ===
brand-primary (replaces void primary #64aeed as a *brand* CTA fill) = gold base #C4A24A. on-brand-primary-ink = canvas #0B0E14 → 7.92 AAA (§4).
brand-primary-pressed (replaces void primary-strong #1d5fa7) = gold-deep #836A2B. Ink atop it must be on-surface #F4F6FB (4.79 AA, §4) — canvas ink fails here (3.74, §2).
brand-accent (replaces void accent-violet #7C5CFC) = gold-bright #D2B875, AAA all four surfaces (§2/§4) — scoped to premium/selected-brand-state moments per the palette policy, not general interactive accent (that stays functional-blue).
glow-gold (replaces the void blue/violet glow in elevation e2/e3): e2 glow = rgba(#C4A24A, 0.20), spec `0 8px 24px rgba(196,162,74,0.20)` + 1px border rgba(255,255,255,.08); e3 glow = rgba(#C4A24A, 0.28), spec `0 16px 40px rgba(196,162,74,0.28)` + 1px border rgba(255,255,255,.10). These are decorative shadow colors, not text-on-background pairs, so WCAG ratio does not apply to them directly — the accessibility obligation here is the alpha/blur values being concrete numbers, which they are; e1 is unchanged (`0 1px 2px rgba(0,0,0,.6)` + 1px border rgba(255,255,255,.06), no glow).
Halo Gold gradient (replaces void 'Halo Primary'): 3-stop linear gradient, gold-deep #836A2B (0%) → gold base #C4A24A (50%) → gold-bright #D2B875 (100%). Each stop's own measured contrast is given in §2 (no new ratio needed — the stops are the ramp). 'Aurora' is retired outright, not replaced: it was a second, louder multi-hue brand gradient, and running a second brand gradient contradicts 'keep gold scarce and deliberate.'
Unresolved and out of scope here: aiGradient (highlightYellow→secondaryPeach, 6 sites) also starts on the now-retired colliding yellow; it was named in neither the carried-forward nor void lists, so I have not redesigned it — flagging it as a gap for the next pass rather than inventing scope.

=== 7. NON-COLOUR TOKENS (carried forward, restated concrete, glow placeholders now filled per §6) ===
Radius: xs 6 / sm 10 / md 16 / lg 24 / full 999 (px).
Spacing (4px grid): 4/8/12/16/20/28/40 (px). Touch target min 48px.
Motion: instant 80ms / fast 150ms / standard 220ms / slow 320ms; easing-standard cubic-bezier(.2,0,0,1); signature spring: mass 1, stiffness 280, damping 22 — reserved for the floating AI button and AI-surface entrances only.
Glass (CHROME ONLY — modals, bottom sheets, nav bar, floating AI button; explicitly excluded from list/feed cards): glass-fill = surface-elevated (#1A2030) at 55% alpha over blur sigma 20; glass-border = on-surface (#F4F6FB) at 12% alpha, 1px.

=== 8. FONT SPECIFICATION ===
Repo-verified (not just survey): pubspec.yaml declares only the Lora family locally (Lora-Regular/Italic/Bold/Medium/SemiBold.ttf on disk, assets/fonts/) and separately lists `google_fonts: ^6.1.0` as a dependency — but a repo-wide grep found zero `GoogleFonts.*` call sites anywhere in lib/. Every current font reference (`fontFamily: 'Urbanist'` ×9 across app_theme.dart both ThemeData.apply() calls, both appBarTheme titleTextStyle, modern_bottom_sheet.dart, frosted_glass_card.dart, bible_reader_tab.dart ×4, and main.dart:293's wordmark; `fontFamily: 'Cinzel'` ×3 in the_walk_screen.dart; `fontFamily: 'monospace'` ×3 in verse_context_debug_screen.dart) is a raw string naming a family that is neither declared in pubspec nor backed by any asset file nor fetched via google_fonts — every one of these renders as a silent platform fallback today. This is the exact defect the token set must not reproduce.
SPEC: family Sora, weights 400 (Regular) / 500 (Medium) / 600 (SemiBold) / 700 (Bold), no italic (not required by any current call site), no serif, no monospace — replacing Urbanist everywhere listed above, including the main.dart wordmark.
RECOMMENDATION: declare Sora LOCALLY — four static .ttf weight files added to assets/fonts/ and registered under `flutter: fonts:` in pubspec.yaml, exactly the pattern already used correctly for Lora (which is declared and on-disk but currently referenced nowhere in code). REASON: google_fonts is already a pubspec dependency but is invoked nowhere — its runtime network-fetch path is untested dead weight in this codebase, and this app has offline-relevant surfaces (Bible reader, prayer features) where a first-load network font fetch risks the identical flash-of-fallback-font failure mode this spec exists to close for Urbanist. Bundling Sora locally, the same way Lora already is, removes that risk entirely and requires no new dependency (google_fonts can stay in pubspec unused, or be dropped — that disposition call belongs to ff-003).
Disposition (named-constant obligation, not a call-site mapping): Cinzel and monospace have no token in Direction B's type system ('No serif, no monospace' is explicit) — both need a disposition in ff-003 (retire to Sora, or carve an explicit bundled-asset exception for the game/debug screens); Lora is declared-and-unreferenced and its fate (drop vs. repurpose) is likewise left open, flagged not decided.
```

## Risks named by the returning agent

1. aiGradient (highlightYellow→secondaryPeach) shares the retired colliding yellow but was named in neither the carried-forward nor void lists in this brief, so it was flagged, not redesigned — a gap for the next pass to pick up explicitly.
2. on-surface-muted is AA-large-only on all four surfaces and only barely clears the 3.0 floor on surface-highlight (3.21) — usable but tight; worth a design review of whether it should ever appear on surface-highlight at all.
3. new-warning (#FA7223) is AA, not AAA, on every surface — an intentional cost of resolving the hue collision, stated in the spec, but downstream reviewers should know it's a deliberate tradeoff, not an oversight.
4. Lora's disposition (drop vs. repurpose, and whether google_fonts stays a dependency at all) is left open — explicitly out of scope here since it's a legacy-asset call, but it is unresolved and someone owns it before ff-003 closes.
5. Cinzel (the_walk_screen.dart) and monospace (verse_context_debug_screen.dart) are flagged as needing disposition per the agent-doc rule that named constants can't be left silent, but resolving them (retire vs. bundle-as-exception) is deliberately deferred, not decided, to stay inside this task's scope boundary.

## Next step as returned

Hand this token set to 20260803-ff-003 for the legacy-constant mapping, per-call-site application rules, and migration order (930-site primaryTeal rename, holyGold/highlightYellow call-site disposition, Cinzel/monospace/Lora resolution, aiGradient follow-up). No approval gate was touched; this is a specification only.