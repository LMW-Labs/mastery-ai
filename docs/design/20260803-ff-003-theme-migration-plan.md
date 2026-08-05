# FaithFeed theme migration plan — Direction B

Accepted output of `20260803-ff-003` (`visual-design`), verdict `accept` at 2026-08-04 18:47 CDT, run `ce592636dcca`.

This file is a verbatim transcription of the accepted return. It is the spec mobile-dev implementation passes are briefed against. Do not edit it to reflect implementation decisions — those belong in the pass briefs and their returns.

## Deliverables returned

- Legacy constant mapping — all 65 survey constants, one line each
- Dark-palette decision (structure kept, values recolored) with stated consequence
- darkGrey disambiguation (fill / divider / inactive)
- primaryCoral + peach-family disambiguation (destructive / selected-premium / generic-interactive / swatch)
- Application rules for call sites mapping to no token
- Migration order across 10 passes + final cleanup, with approximate call-site counts per pass

## Specification

```text
Mapped all 65 constants named in the measured survey (theme_members) onto Direction B, verified directly against lib/theme/app_theme.dart and repo greps for darkGrey/primaryCoral usage patterns. Full spec below.

=== DARK-PALETTE DECISION (choice + consequence) ===
CHOICE: keep the legacy dark block's STRUCTURE (a 4-step surface ladder + 3-step text ladder) but RECOLOR every value onto Direction B's new dark hexes, rather than keeping the legacy near-black/warm-grey values (#131312/#1F1F1E/#252524/#2E2E2B, text #FAFAFA/#B8B8C8/#8A8A9A) which were tuned for the old blue-branded system, not the gold anchor. The legacy dark block's brand-colored members (mainBlue, lightBlue-as-brand, primaryPurple*, accentPurple, highlightYellow-as-brand, the coral/peach family, likeRed) are retired or refolded per the per-constant table below, in favor of the gold ramp + functional-blue.
CONSEQUENCE: every dark-mode call site keeps its structural role (background/surface/text-on-surface still exist and still resolve) but ~3,550 call sites across the repo change their rendered hex in one coordinated set of passes, not a handful of screens — this is a full app re-skin, not a touch-up. Anyone comparing before/after screenshots will see every screen shift from warm near-black + blue/purple/yellow/coral accents to cool navy-black + gold + functional-blue, in the same release window covered by the passes below.

=== LEGACY CONSTANT MAPPING (all 65 survey keys) ===
Format: constant (count) → disposition.
primaryTeal (930) → RENAME to functional-blue (#64AEED), identical hex, ff-002 §3 rationale (rename not recolor). EXCEPTION: any single site serving as the app's primary brand-CTA fill (elevatedButton/FAB/primary-action backgroundColor role) goes to brand-primary (gold) instead — flag while touching the 930, don't defer.
lightBlue (22) → same disposition as primaryTeal (its alias source): rename to functional-blue, same exception.
onSurfaceVariant (807) → MAP to on-surface-variant (#A9B2C6).
onSurface (614) → MAP to on-surface (#F4F6FB).
surface (370) → MAP to surface (#12161F).
surfaceElevated (27) → MAP to surface-elevated (#1A2030).
surfaceHighlight (1) → MAP to surface-highlight (#232B40).
darkBackground (89) → MAP to canvas (#0B0E14).
background (15, alias of darkBackground) → MAP to canvas (#0B0E14), same as darkBackground.
onSurfaceMuted (12) → MAP to on-surface-muted (#6E7893); carry forward the AA-large-only restriction, avoid on surface-highlight.
onPrimary (9) → DISAMBIGUATE by the fill it sits on: paired with brand-primary/brand-primary-pressed fill → on-brand-primary-ink / on-brand-primary-pressed-ink; paired with a neutral surface fill → on-surface. Most current sites (elevatedButtonTheme/FAB foregroundColor) will become on-brand-primary-ink once their fills move to gold per the functional-blue/brand-CTA exception above.
darkGrey (76) → DISAMBIGUATED, not wholesale (see dedicated section below).
primaryCoral (101) → DISAMBIGUATED, not wholesale (see dedicated section below; also covers its alias family).
softPeach (23, = secondaryPeach) → same coral/peach family rule as primaryCoral.
secondaryPeach (2, base of the family) → same coral/peach family rule.
accentAmber (1, = secondaryPeach) → same coral/peach family rule.
lightPurple (2, = secondaryPeach — misnamed, it's peach not purple) → same coral/peach family rule.
likeRed (16) → RETIRE as a distinct hue (#A13322 has no equivalent in Direction B's 3-color status set); MAP call sites to error (#F87171). COST: the like-heart shifts from a deliberate brick-red brand accent to the generic error red — dev notes say 'keep for likes only', so this is a real loss of distinctiveness; if the product wants a dedicated like-affordance color back, that requires a token-set amendment (out of scope here, since re-deriving the token set is explicitly off-limits).
mintGreen (40) → MAP to success (#34D399); used for upvotes/creator badges/positive indicators, nearest semantic match. Cost: pastel mint → saturated green, a visible hue/saturation shift.
highlightYellow (22) → DISAMBIGUATE: default/unselected/inactive states (e.g. the unprayed half of `isPrayed ? primaryCoral : highlightYellow`) → on-surface-variant (neutral, no longer a brand hue); active/selected/'prayed'/premium-moment states → gold (base #C4A24A) for larger fills or gold-bright (#D2B875) for icons/small text; any literal caution/warning-adjacent use → new-warning (#FA7223). Default to gold-bright when a site doesn't clearly fit a bucket (AAA everywhere, safest default).
holyGold (22) → MAP directly to gold (#C4A24A) — ff-002 §5 already resolved this explicitly ('its identity folds into the gold token/ramp'), a clean 1:1 fold, no ambiguity.
warningAmber (7) → MAP to new-warning (#FA7223).
errorRed (7) → MAP to error (#F87171).
successGreen (10) → MAP to success (#34D399).
aiGradient (6) → RETIRE the 2-stop yellow→peach gradient (both stops are retired hues); REPLACE with a flat brand-accent fill (gold-bright #D2B875) rather than a new gradient, so 'AI moments' still read as special without violating the 'keep gold scarce, one gradient only' policy that already retired 'Aurora'. This is the disposition for the exact gap ff-002 flagged and left to this task.
accentPurple (5, = mainBlue) → MAP to brand-primary-pressed (gold-deep #836A2B) — mainBlue's hex (#1d5fa7) is exactly ff-002's 'void primary-strong', already given a direct replacement.
primaryPurple (2, = mainBlue) → same as accentPurple: MAP to brand-primary-pressed (gold-deep).
mainBlue (4) → MAP to brand-primary-pressed (gold-deep #836A2B), per §6's direct replacement of void primary-strong #1d5fa7.
primaryGradient (4, mainBlue→lightBlue) → RETIRE, REPLACE with Halo Gold gradient (gold-deep→gold→gold-bright), a brand gradient using void-blue stops.
logoGradient (2, mainBlue→lightBlue) → RETIRE, REPLACE with Halo Gold gradient, same reasoning (this is brand/wordmark chrome, not a decorative post-background gradient).
glassBorder (5) → MAP to glass-border (on-surface at 12% alpha, 1px) — CHROME ONLY (modals/sheets/nav bar/floating AI button) per §7. Application rule: any current glassBorder site on a list/feed card must drop the glass treatment entirely, not receive the token (list/feed cards are explicitly excluded from glass in Direction B).
glassWhite (4) → MAP to glass-fill (surface-elevated at 55% alpha over blur 20) — same chrome-only scope restriction and exclusion rule as glassBorder.
hairlineThickness (5) → RETAINED unchanged (0.5px); Direction B doesn't redefine this thickness, no conflict.
cardRadius (4, =12px) → RETIRE the 12px value (off Direction B's radius scale of 6/10/16/24/999); REMAP to radius-md (16px), the nearest scale step for card-sized elements. Cost: a visible +4px softening on every card corner.
cardBorderWidth (1, =0.65px) → RETIRE the 0.65 value (no matching thickness token); REMAP to hairlineThickness (0.5px), nearest defined thickness. Cost: borders read marginally thinner.
cardMargin (1, EdgeInsets(h:16,v:6)) → MAP horizontal to spacing-16 (exact match); REMAP vertical 6→spacing-8 (nearest scale step, off-grid value doesn't exist).
cardPadding (1, EdgeInsets(h:16,v:12)) → MAP cleanly to spacing-16 / spacing-12 — both are exact matches on the 4/8/12/16/20/28/40 scale, no rounding needed.
darkTheme (1) → RETAINED — this is the ThemeData object Direction B rebuilds in place and the thing main.dart:116 points to after the flip; not a legacy constant to migrate away from, it's the migration target.
lightTheme (2) → RETIRE outright per ff-002's explicit mandate; main.dart:116 swaps to AppTheme.darkTheme.
lightBackground (1) → RETIRE (light block); REPOINT its one call site to canvas (#0B0E14).
lightSurface (20) → RETIRE (light block); REPOINT to surface (#12161F).
lightSurfaceHighlight (15) → RETIRE (light block); REPOINT to surface-highlight (#232B40).
lightOnSurface (104) → RETIRE (light block); REPOINT to on-surface (#F4F6FB).
lightOnSurfaceVariant (91) → RETIRE (light block); REPOINT to on-surface-variant (#A9B2C6).
lightOnSurfaceMuted (21) → RETIRE (light block); REPOINT to on-surface-muted (#6E7893).
lightBackgroundGradient (15) → RETIRE — Direction B's canvas is a flat color, no dark gradient-background token exists. REPOINT call sites to a flat canvas (#0B0E14) fill (this is the 'maps to nothing' case for a gradient, resolved by the general application rule below).
lightElevation1 (4) → RETIRE (light block); REPOINT to e1 (unchanged spec: `0 1px 2px rgba(0,0,0,.6)` + 1px border rgba(255,255,255,.06)).
lightElevation2 (2) → RETIRE (light block); REPOINT to e2 gold glow (`0 8px 24px rgba(196,162,74,0.20)` + border).
lightElevation3 (3) → RETIRE (light block); REPOINT to e3 gold glow (`0 16px 40px rgba(196,162,74,0.28)` + border).
primaryBlue (91, light-theme accent) → RETIRE (light block); its generic-interactive-control call sites (buttons, switches, sliders, focus borders, tab indicators) REPOINT to functional-blue, same brand-CTA exception as primaryTeal.
secondaryIndigo (1) → RETIRE (light block); no external call site found (definitional use only inside ColorScheme.light), no repoint needed.
berryBlastGradient / cherryBlossomGradient / deepOceanGradient / fireGlowGradient / forestGreenGradient / lavenderMistGradient / mintFreshGradient / northernLightsGradient / oceanBreezeGradient / peachyKeenGradient / purpleHazeGradient / roseGoldGradient / skyBlueGradient (2 sites each, 26 total) → RETAINED, unchanged. These are the 'Decorative Post Background Gradients (Facebook-style)' — a user-selectable content palette for post backgrounds, not brand/system chrome, and they don't use any retired brand hue. Direction B's gold-scarcity policy governs brand gradients (Halo Gold vs the retired Aurora/void gradients), not this independent decorative list. Flagged for ui-ux/product if the list itself needs curation — out of this task's scope.
_" (1) → NOT a constant — this is the survey's grep matching `AppTheme._()`, the class's private constructor. No value, no disposition needed, excluded from the table.

=== darkGrey (76 sites) DISAMBIGUATED PER USE ===
darkGrey (#1E1E1E) is not one thing in the codebase; grep shows three distinct roles, so it gets three destinations:
1. FILL role (CircleAvatar/Container backgroundColor, TextField fillColor, chip/snackbar/badge backgroundColor, chat-bubble background) → surface-elevated (#1A2030). Reason: darkGrey was already a step lighter than the old background, matching surface-elevated's 'raised panel' role.
2. DIVIDER/BORDER role (Divider widget color, BorderSide, top/bottom Border on headers, input borders) → surface-highlight (#232B40). Reason: a divider needs to read as a visible seam against surrounding fills; surface-highlight is the ladder's lightest neutral step, giving borders enough separation without inventing a new hairline color.
3. INACTIVE/DISABLED control role (Slider inactiveColor, disabledBackgroundColor with alpha) → surface (#12161F). Reason: disabled/inactive states should recede toward the canvas, not pop as an elevated fill.
Mobile-dev applies whichever bucket matches each call site's widget role; do not default all 76 sites to one token.

=== primaryCoral (101 sites, plus its softPeach/secondaryPeach/accentAmber/lightPurple aliases) DISAMBIGUATED PER USE ===
All of these names share one underlying hex (#F99985) but serve different roles:
1. DESTRUCTIVE/ERROR role (delete/remove/reject/clear/error_outline icons and buttons) → error (#F87171).
2. SELECTED/ACTIVE/PREMIUM-MOMENT role (isMember/isPrayed/isCreator-style toggles, badges signaling an activated or premium state) → brand-accent / gold-bright (#D2B875) — this is exactly the 'premium/selected-brand-state moment' §6 reserves gold-bright for. Concrete example: `isPrayed ? primaryCoral : highlightYellow` becomes `isPrayed ? gold-bright : on-surface-variant` — active state goes gold, default state goes neutral, preserving the toggle's visual distinction (mapping both halves to gold would erase it).
3. GENERIC DECORATIVE/INTERACTIVE role (tab indicator/label color, generic icon accents, borders, default banner/snackbar backgroundColor not tied to a status or a selected state) → functional-blue (#64AEED), consistent with §6 ('interactive accent stays functional-blue').
4. LITERAL SWATCH-PICKER OPTION ('Coral' entry in the post-background color picker list) → retired as a distinct hue; the picker's swatch list is a ui-ux/content decision, not a token-system one — flagged, not resolved here.
Mobile-dev applies the bucket matching each call site's role; do not map primaryCoral wholesale to one token.

=== APPLICATION RULES: call sites whose current value maps to no token ===
1. Any call site currently rendering a light-theme structural role (background/surface/text tier or a light elevation) whose named constant retires → repoint to the parallel step in the new dark ladder (canvas/surface/surface-elevated/surface-highlight; on-surface/on-surface-variant/on-surface-muted; e1/e2/e3), never left on the deleted light value.
2. Any gradient built from retired hues with no direct gradient replacement (lightBackgroundGradient, aiGradient) collapses to a flat fill using the nearest single token from its former stops' successor roles (canvas for lightBackgroundGradient, gold-bright for aiGradient) rather than inventing a new gradient.
3. Any off-scale numeric legacy value (radius 12, border-width 0.65, spacing 6) rounds to the nearest defined step on Direction B's radius/spacing/thickness scale, rounding toward the larger neighbor for radius/spacing and the smaller neighbor for hairline thickness, and the rounding direction/cost is stated in the mapping line, never silently snapped.
4. Any semantically distinct legacy hex with no equivalent in the 3-color status set or the gold/blue palette (likeRed) folds into the nearest existing semantic or brand token, with the loss of distinctiveness named explicitly as a cost, not hidden.
5. General fallback: if a call site is discovered during migration that used a legacy constant not resolvable by rules 1–4 (e.g. a raw hex nobody named), mobile-dev must pick the nearest token by ROLE — surface-ladder position for a fill, text-ladder position for a foreground, nearest semantic status color for a state indicator — and log the site in a punch list for design review. Never invent an ad hoc hex and never leave the legacy literal in place silently.

=== MIGRATION ORDER (by leverage, additive-before-deletion, with approximate call-site counts) ===
Pass 1 — Foundation (additive, non-breaking, 0 external call sites beyond main.dart:116/119): rebuild AppTheme.darkTheme with every Direction B token value; add the new named tokens (functional-blue, gold ramp, error/success/new-warning, canvas/surface ladder, on-surface ladder, brand-primary/pressed/accent, e1–e3, Halo Gold gradient, glass-fill/border, radius/spacing/motion scale); flip main.dart:116 to `theme: AppTheme.darkTheme` and main.dart:119's builder Container to canvas. Legacy constants stay defined and compiling — nothing else breaks yet. This must run first; every later pass depends on these names existing.
Pass 2 — Surface & text ladder (~1,935 sites: darkBackground 89 + background 15 + surface 370 + surfaceElevated 27 + surfaceHighlight 1 + onSurface 614 + onSurfaceVariant 807 + onSurfaceMuted 12): the structural skeleton under every screen. Within this pass, sequence lib/widgets/* files before lib/screens/* — shared widgets (verse_actions_modal, enhanced_post_card, premium_badge, modern_bottom_sheet, frosted_glass_card, etc.) are consumed by many screens, so fixing them first means screen-level work in later passes isn't re-touching the same call site.
Pass 3 — Functional-blue rename (~952 sites: primaryTeal 930 + lightBlue 22): mechanical rename, identical hex, lowest risk, but flag any brand-CTA-fill exception discovered while touching these sites (routes to brand-primary/gold instead).
Pass 4 — Legacy light-theme family retirement (~370 sites: lightOnSurface 104 + lightOnSurfaceVariant 91 + lightOnSurfaceMuted 21 + lightSurface 20 + lightSurfaceHighlight 15 + lightBackground 1 + lightBackgroundGradient 15 + lightElevation1 4 + lightElevation2 2 + lightElevation3 3 + primaryBlue 91 + secondaryIndigo 1 + lightTheme 2): repointed onto the dark ladder established in Pass 2, so targets are already stable when this pass runs.
Pass 5 — Brand-void retirement, blue/purple-as-brand → gold (~17 sites: mainBlue 4 + primaryPurple 2 + accentPurple 5 + primaryGradient 4 + logoGradient 2): small but high-visibility (logo/wordmark chrome); sequenced after the functional-blue rename so blue-as-functional and blue-as-brand aren't sorted in the same motion.
Pass 6 — Gold-family fold & status colors (~108 sites: holyGold 22 + highlightYellow 22 + warningAmber 7 + errorRed 7 + successGreen 10 + mintGreen 40): the semantic table and gold-ramp brand-moments land together since they share the same dependency.
Pass 7 — Coral/peach family disambiguation (~145 sites: primaryCoral 101 + softPeach 23 + secondaryPeach 2 + accentAmber 1 + lightPurple 2 + likeRed 16): depends on knowing which sites are 'selected/prayed/premium' gold-moments decided in Pass 6 — toggle pairs like `isPrayed ? coral : highlightYellow` must be edited together in whichever pass first touches that call site, not split across passes.
Pass 8 — Structural misc (~12 sites: cardRadius 4 + cardBorderWidth 1 + cardMargin 1 + cardPadding 1 + hairlineThickness 5): mechanical, no cross-dependency, placed late only because it's low-value/low-risk, not because it's blocked.
Pass 9 — Glass chrome re-scoping (~9 sites: glassBorder 5 + glassWhite 4): confirm none of the 9 sites is a list/feed card (excluded by spec); any that are lose the glass treatment outright rather than getting a chrome token misapplied.
Pass 10 — aiGradient disposition (6 sites): replace the 2-stop gradient with a flat gold-bright fill.
Final Cleanup Pass — Deletion (0 new call sites): only after Passes 2–10 are verified complete (grep confirms zero remaining references to every renamed/retired constant name) delete the legacy constant definitions from app_theme.dart, including the entire LIGHT THEME COLORS block and AppTheme.lightTheme. Deleting earlier is exactly the pass-conflict this order is built to avoid — an unused light path left dormant is how ff-002 warned it gets silently reactivated.
Out of migration scope (0 sites need touching): the 13 decorative post-background gradients (26 sites) stay as-is.

The five items ff-002 explicitly left open (Cinzel, monospace, Lora, google_fonts, aiGradient) — only aiGradient was in this task's survey scope and is dispositioned above. Cinzel, monospace, Lora, and google_fonts are font/dependency dispositions outside the 'legacy constant' survey this brief scoped me to (they're not in theme_members); flagging that they remain open and naming them in risks so they aren't lost before mobile-dev is briefed.
```

## Risks named by the returning agent

1. likeRed folds into error with a stated loss of brand distinctiveness (brick-red 'like' color becomes generic error red) — if the product wants that distinctiveness back, it requires a token-set amendment, which is out of this task's scope.
2. The 930+22-site functional-blue rename (Pass 3) and the light-family repoint (Pass 4) both assume no additional 'brand-CTA-fill' exceptions beyond what a grep-level read surfaced; a small number of sites may need reclassifying to brand-primary during actual implementation, which is expected and named as an in-pass flag, not a blocker.
3. Cinzel (3 sites), monospace (3 sites), Lora, and google_fonts remain open dispositions from ff-002's five deferred items — they are not legacy 'constants' in the theme_members survey this task was scoped to, so they were not addressed here and still need an owner before mobile-dev's font work is briefed.
4. The 13 decorative post-background gradients (26 sites) were judged out of brand-token scope and left untouched; if product/ui-ux disagrees with that scope boundary, that's a call for them to make, not a silent gap.
5. Per-call-site counts for darkGrey and primaryCoral's three/four use-buckets are not separately measured in the survey (only the aggregate 76 and 101) — mobile-dev applies the stated role-based rule at each site rather than a pre-computed split; this was a deliberate choice to avoid re-deriving measurement data (ff-002's/the survey's job), not an omission.

## Next step as returned

Hand this mapping, disambiguation, application rules, and 10-pass migration order to mobile-dev for implementation planning; no approval gate was touched, so no further sign-off is required from this task before that handoff.