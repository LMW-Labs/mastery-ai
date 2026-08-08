# FaithFeed — UI Review Brief

Handoff doc for mobile-dev / UI agents evaluating whether the app's look can be improved.
Generated 2026-08-02 against the current working tree.

**Stack:** Flutter 3.35.5 / Dart 3.9.2, Material 3 off (see below), Provider state, Firebase backend.
**Scope of the UI surface:** 61 screens + 29 widgets, ~46,000 lines under `lib/screens/` and `lib/widgets/`.

> ⚠️ The app does **not** compile right now — 87 errors from an in-progress `_archive/` move.
> Visual review can proceed from source, but you cannot run the app until those are fixed.
> Affected files are marked 🔴 below.

---

## 1. Read these first — the design system (1,057 lines)

These four files define essentially the entire visual language. Everything else consumes them.

| File | Lines | What's in it |
|---|---|---|
| `lib/theme/app_theme.dart` | 863 | All colors, gradients, shadows, text themes, both `ThemeData` objects, glassmorphism helpers |
| `lib/theme/app_icons.dart` | 194 | Icon mapping layer (Phosphor / Lucide / FontAwesome wrappers) |
| `lib/main.dart` | 293 | Theme wiring — `MaterialApp` at L95–102, forces `AppTheme.lightTheme` |
| `pubspec.yaml` | — | Font declarations (L~200) and the UI package set |

### Structure of `app_theme.dart`

```
L11–33    Light palette         — backgrounds, text, primaryBlue #3B82F6, secondaryIndigo #6366F1,
                                  glass colors, status colors
L40–87    Dark palette          — "Legacy - Keeping for reference", logo blues #1d5fa7 / #64aeed,
                                  highlightYellow, secondaryPeach, likeRed
L47–56    Card density tokens   — cardRadius 12, cardPadding, cardMargin, borderWidth 0.65
L69–81    Legacy alias colors   — primaryPurple → mainBlue, accentAmber → secondaryPeach, etc.
L90–254   Gradients             — 4 structural + 16 decorative post backgrounds
L257–344  Shadow system         — glowShadow*, elevatedShadow, subtleShadow,
                                  lightElevation1/2/3, blueGlow
L349–414  Decoration helpers    — glassmorphicContainer(), frostedGlassDecoration(), elevatedCard()
L417–634  darkTheme  ThemeData  — includes a full TextTheme (L435–539)
L640–863  lightTheme ThemeData  — includes a full TextTheme (L658–762)   ← the only one in use
```

---

## 2. Shared visual components (the reusable look)

Change these and the change propagates app-wide. This is the highest-leverage tier.

**Surfaces & containers**
```
 177  lib/widgets/frosted_glass_card.dart
 137  lib/widgets/modern_card.dart
  60  lib/widgets/faith_card.dart
  98  lib/widgets/book_page_background.dart
 515  lib/widgets/modern_bottom_sheet.dart
```

**Controls & primitives**
```
 232  lib/widgets/modern_buttons.dart
 156  lib/widgets/floating_ai_button.dart
  26  lib/widgets/app_gradient_icon.dart
  25  lib/widgets/faith_icon.dart
  31  lib/widgets/faith_divider.dart
```

**States — loading / empty / offline**
```
 429  lib/widgets/skeleton_loading.dart
 348  lib/widgets/empty_states.dart
 360  lib/widgets/offline_indicator.dart
 387  lib/widgets/infinite_scroll.dart
```

**Media**
```
 352  lib/widgets/optimized_image.dart
 217  lib/widgets/hd_cached_image.dart
```

**Domain components (heavily styled, high visibility)**
```
1045  lib/widgets/enhanced_post_card.dart      🔴 2   ← the feed card; most-seen component in the app
1821  lib/widgets/verse_actions_modal.dart            ← largest widget in the repo
 666  lib/widgets/annotations/annotation_card.dart
 525  lib/widgets/annotations/verse_annotation_panel.dart
 364  lib/widgets/annotations/add_annotation_form.dart
 453  lib/widgets/verse_picker_modal.dart
 227  lib/widgets/daily_verse_card.dart
 151  lib/widgets/ai_commentary_card.dart
 354  lib/widgets/swipeable_card.dart
 116  lib/widgets/profile_switcher.dart
```

---

## 3. Highest-traffic screens (what a user actually sees)

Ranked by how much of the visible surface they own, not by line count.

```
1581  lib/screens/main/main_screen.dart              🔴 6   app shell, bottom nav, app bar
 416  lib/screens/main/tabs/home_tab.dart            🔴 4   the feed
1573  lib/screens/main/tabs/bible_reader_tab.dart    🔴 3   reader — the core product surface
 433  lib/screens/main/tabs/explore_tab.dart         🔴 8
 478  lib/screens/main/tabs/study_tab.dart
 379  lib/screens/main/tabs/prayer_wall_tab.dart
1633  lib/screens/main/create_post_modal.dart        🔴 9   + 8 sub-widgets in create_post/widgets/
 300  lib/screens/auth/login_screen.dart                    first impression, and currently broken in prod
 395  lib/screens/auth/signup_screen.dart
1198  lib/screens/profile/my_profile_screen.dart
1167  lib/screens/profile/user_profile_view_screen.dart
1338  lib/screens/main/account_settings_screen.dart  🔴 2
1674  lib/screens/bible/widgets/verse_community_tab.dart
1395  lib/screens/main/ai_library_screen.dart
```

---

## 4. Where the design system is being bypassed

Measured across all 90 UI files:

| Pattern | Count | Meaning |
|---|---:|---|
| `AppTheme.*` references | 2,569 | system is broadly adopted |
| Inline `TextStyle(` | 1,084 | typography largely hand-written per call site |
| `Colors.<name>` + `Color(0x…)` literals | 724 | off-system color |
| `BorderRadius.circular(` | 395 | radius rarely uses `AppTheme.cardRadius` |
| `withValues(` | 289 | migrated |
| `withOpacity(` | 124 | **deprecated**, still present — precision loss |
| `LinearGradient(` inline | 48 | in addition to the 20 named gradients |
| `Theme.of(context)` | 44 | ThemeData/TextTheme almost never consumed |
| `BackdropFilter(` | 13 | actual glassmorphism blur is rare despite the naming |

**Worst offenders for hardcoded color** (these diverge most from the system):

```
56  screens/main/ai_tools/ai_study_partner_screen.dart   🔴 20
38  screens/main/ai_library_screen.dart
30  screens/main/tabs/bible_reader_tab.dart              🔴 3
29  screens/main/tabs/explore_tab.dart                   🔴 8   (29 off-system vs only 10 AppTheme refs)
28  screens/main/ai_tools/thematic_guidance_screen.dart
25  screens/main/main_screen.dart                        🔴 6
21  widgets/verse_actions_modal.dart
19  screens/main/ai_tools_screen.dart                           (19 off-system vs 0 AppTheme refs)
```

**Most hand-written typography:**

```
58 inline TextStyles  screens/main/account_settings_screen.dart
56                    screens/bible/widgets/verse_community_tab.dart
48                    screens/main/ai_library_screen.dart
48                    screens/notes/notes_feed_screen.dart
45                    widgets/verse_actions_modal.dart
44                    screens/onboarding/complete_onboarding_screen.dart
```

---

## 5. Known issues worth confirming before redesign work

**a) The app's chosen font is not shipped.**
`app_theme.dart` sets `fontFamily: 'Urbanist'` at L540, L592, L763, L824. No Urbanist font is
declared in `pubspec.yaml` and none exists in `assets/fonts/` — only Lora. Flutter fails silently
and falls back to Roboto, so **the entire app currently renders in Roboto**, not the intended
typeface. `google_fonts: ^6.1.0` is a dependency but is never called (0 usages).
Also: `Lora-Medium.ttf` and `Lora-SemiBold.ttf` are on disk but not declared, so those weights
are unavailable too.

**b) Two complete themes, one dead.**
`darkTheme` (L417–634, ~220 lines incl. a full TextTheme) is labeled legacy and never referenced —
`main.dart:97` passes only `theme: AppTheme.lightTheme` with no `darkTheme:` argument. There is no
dark mode. The dark palette constants (`surface`, `onSurface`, `background`, …) are nonetheless
still used by name throughout the UI, which is why some surfaces may read oddly against the light
background.

**c) Two color identities coexist.**
Logo blues `#1d5fa7` / `#64aeed` (dark-theme era) vs light-theme `#3B82F6` / `#6366F1`. Plus a
legacy alias block at L69–81 where `primaryPurple`, `accentAmber`, `accentPurple`, `primaryCoral`,
`lightPurple`, `holyGold` all now point at blues and peaches — call sites still read as purple/amber.

**d) Glassmorphism is mostly nominal.**
`glassmorphism: ^3.0.0` is a dependency, three glass helpers exist in the theme, but only 13
`BackdropFilter` calls exist across 90 files. Decide whether to commit to the effect or drop it.

**e) Declared-but-unused UI packages.** Verify before pruning (task #9):
`glassmorphism`, `shimmer` (own skeleton system exists), `flutter_animate`, `lucide_icons`
alongside `phosphor_flutter` and `font_awesome_flutter` — three icon sets.

**f) 16 decorative post gradients** (L153–254) drive Facebook-style post backgrounds in
`create_post_modal.dart`. Confirm this feature survives the refactor before styling it.

**g) Dead code inside live components.**
`verse_actions_modal.dart` — unused `_mapResultToVerse`, `_buildShimmerCard`, and an unused import
of `verse_annotation_panel.dart`. `enhanced_post_card.dart` — unused `shimmer` and
`cached_network_image` imports.

**h) Two parallel note UIs.**
`widgets/add_verse_note_sheet.dart` (311L, 🔴 5 errors) vs `widgets/annotations/*` (1,555L, working).
The annotations tree is the intended survivor per the refactor plan — don't style the former.

---

## 6. Suggested review order

1. `lib/theme/app_theme.dart` — the whole system, one file.
2. `lib/widgets/enhanced_post_card.dart` — most-seen component.
3. `lib/screens/main/main_screen.dart` — shell, nav, app bar.
4. `lib/screens/main/tabs/bible_reader_tab.dart` — core product surface.
5. `lib/screens/auth/login_screen.dart` + `signup_screen.dart` — first impression.
6. The shared-component tier in §2 — highest leverage per line changed.

Fixing item **5(a)** alone (ship the real font) changes every screen in the app.
