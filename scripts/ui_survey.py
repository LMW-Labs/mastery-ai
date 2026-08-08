"""Measure a Flutter app's visual system, so a brief about it can be regenerated.

    python scripts/ui_survey.py <app root> [--json] [--out FILE]

Costs nothing and calls no model. It reads files and counts.

This exists because the brief it feeds was written by hand, and hand-written
measurements of a 120-file codebase go stale silently and are wrong quietly.
The version it replaces claimed the app did not compile — 87 errors from an
`_archive/` move — against a repository with no `_archive/` directory and zero
errors in `lib/`, and it undercounted every repo-wide figure by 19-32% because
whole feature directories were never walked. Neither error is visible by reading
the document; both are obvious the moment the numbers are re-derived.

So the rule this script enforces is that the numbers are *generated*. Re-run it
and rebuild the brief from its output rather than editing figures in place.

Deliberately standalone: no `mastery` imports, no third-party dependencies. It
describes a different repository than the one it lives in, and it has to run on
a machine where only the app is checked out.

A count here is evidence of a pattern's *frequency*, not proof of a defect. The
per-file rankings say where the visual system is most often bypassed; they do
not say those files are wrong. That judgement belongs to the agent reading them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Directories walked for the UI inventory. Anything outside these is counted in
# the repo-wide totals but excluded from the file inventory and the rankings --
# the point of the inventory is the surfaces a user sees.
UI_DIRS = ("lib/screens", "lib/widgets")

# Where the token definitions live, reported separately because they are the
# thing being bypassed rather than an instance of bypassing it.
THEME_DIR = "lib/theme"

# Each pattern is (label, compiled regex). Counted per file and summed.
#
# These are lexical counts on source text, which is the honest description of
# what they are: a `Color(0xFF...)` inside a comment or a string still counts.
# The alternative is parsing Dart, which is a far larger tool than the question
# needs -- the figures are used to rank files against each other, and a
# consistent small overcount does not change a ranking.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # The system being bypassed: a style written at the call site.
    ("inline_text_style", re.compile(r"\bTextStyle\s*\(")),
    # A colour that is not a token: literal ARGB, or a Colors.* constant.
    ("hardcoded_color", re.compile(r"Color\s*\(\s*0x[0-9a-fA-F]{6,8}|\bColors\.[a-zA-Z]")),
    # A radius written by hand rather than taken from a shape scale.
    ("raw_border_radius", re.compile(r"BorderRadius\.circular\s*\(")),
    # The system being used. Low counts here against high counts above is the
    # shape of "there is a theme, and nothing reads it".
    ("theme_of_context", re.compile(r"Theme\.of\s*\(\s*context\s*\)")),
    # The premium effect, where it is actually implemented.
    ("backdrop_filter", re.compile(r"\bBackdropFilter\b")),
    # Gradient use, structural and decorative alike.
    ("gradient", re.compile(r"\bLinearGradient\b|\bRadialGradient\b|\bSweepGradient\b")),
    # Elevation set at the call site rather than by a ladder.
    ("inline_elevation", re.compile(r"\belevation\s*:")),
    # A font family named in code. The family names themselves are collected
    # separately below; this is the count of sites naming one.
    ("font_family_site", re.compile(r"fontFamily\s*:")),
)

# Font families named anywhere in Dart source, captured so the brief can say
# which are declared, which are on disk, and which are neither.
FONT_FAMILY = re.compile(r"""fontFamily\s*:\s*['"]([^'"]+)['"]""")

# `AppTheme.somethingGradient`, `AppTheme.primaryPurple` -- references to the
# theme class's own members, which is how legacy constants are found without
# hardcoding their names.
THEME_MEMBER = re.compile(r"\bAppTheme\.([A-Za-z_][A-Za-z0-9_]*)")

# Families declared to the build. Matched against pubspec's `fonts:` section.
PUBSPEC_FAMILY = re.compile(r"^\s*-?\s*family:\s*(.+?)\s*$", re.MULTILINE)


def _read(path: Path) -> str:
    """Source text, or empty on a file that cannot be decoded.

    Never raises. A survey that dies on one unreadable file reports nothing
    about the other 119, which is strictly worse than reporting 119 and saying
    which one it skipped.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def survey(root: Path) -> dict:
    """Walk the app and return every figure the brief needs, as data."""
    problems: list[str] = []

    dart_files = sorted(p for p in root.rglob("*.dart") if p.is_file())
    if not dart_files:
        problems.append(
            f"no .dart files under {root} -- is this a Flutter app root, and not "
            f"its parent or its android/ subdirectory?"
        )

    ui_roots = [root / d for d in UI_DIRS]
    for directory in ui_roots:
        if not directory.exists():
            problems.append(f"{directory} does not exist; its files are absent from the inventory")

    def in_ui(path: Path) -> bool:
        return any(_is_within(path, directory) for directory in ui_roots)

    inventory: list[dict] = []
    repo_totals: dict[str, int] = {name: 0 for name, _ in PATTERNS}
    ui_totals: dict[str, int] = {name: 0 for name, _ in PATTERNS}
    families: dict[str, int] = {}
    theme_members: dict[str, int] = {}
    total_lines = 0
    ui_lines = 0

    for path in dart_files:
        text = _read(path)
        lines = text.count("\n") + 1 if text else 0
        total_lines += lines

        counts = {name: len(pattern.findall(text)) for name, pattern in PATTERNS}
        for name, value in counts.items():
            repo_totals[name] += value

        for family in FONT_FAMILY.findall(text):
            families[family] = families.get(family, 0) + 1
        for member in THEME_MEMBER.findall(text):
            theme_members[member] = theme_members.get(member, 0) + 1

        if not in_ui(path):
            continue

        ui_lines += lines
        for name, value in counts.items():
            ui_totals[name] += value
        inventory.append(
            {
                "path": path.relative_to(root).as_posix(),
                "lines": lines,
                "bytes": path.stat().st_size,
                "counts": counts,
            }
        )

    # Rankings, over the UI inventory only. `bytes` is carried because it is the
    # figure that decides whether a file can be pasted into a brief at all --
    # caps.max_context_bytes is 60,000 and an over-limit payload is rejected
    # rather than truncated. A file that cannot be pasted has to be read from
    # cwd, which is a fact about how to brief it, not about its quality.
    rankings = {
        name: [
            {"path": entry["path"], "count": entry["counts"][name]}
            for entry in sorted(
                inventory, key=lambda e: (-e["counts"][name], e["path"])
            )
            if entry["counts"][name] > 0
        ][:20]
        for name, _ in PATTERNS
    }
    rankings["largest_files"] = [
        {"path": entry["path"], "bytes": entry["bytes"], "lines": entry["lines"]}
        for entry in sorted(inventory, key=lambda e: -e["bytes"])[:20]
    ]

    return {
        "app_root": str(root),
        "problems": problems,
        "inventory": {
            "ui_files": len(inventory),
            "ui_lines": ui_lines,
            "dart_files_repo_wide": len(dart_files),
            "dart_lines_repo_wide": total_lines,
            "directories_walked": list(UI_DIRS),
            "files": inventory,
        },
        "counts": {"ui": ui_totals, "repo_wide": repo_totals},
        "fonts": _fonts(root, families),
        "theme_members": dict(
            sorted(theme_members.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "rankings": rankings,
        # How many UI files could be pasted into a brief at all. The rest have
        # to be read from `cwd`, which is why config/faithfeed.json exists.
        "pasteable_at_60kb": sum(1 for e in inventory if e["bytes"] <= 60_000),
        "too_large_to_paste": sorted(
            (e["path"], e["bytes"]) for e in inventory if e["bytes"] > 60_000
        ),
    }


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _fonts(root: Path, referenced: dict[str, int]) -> dict:
    """Which families are named in code, declared to the build, and on disk.

    The three lists rarely agree, and every way they disagree is a real defect:
    a family named in code but not declared renders as a silent fallback, and a
    family on disk but undeclared is an asset nobody can use.
    """
    pubspec = _read(root / "pubspec.yaml")
    declared = sorted({m.strip().strip("'\"") for m in PUBSPEC_FAMILY.findall(pubspec)})

    font_dir = root / "assets" / "fonts"
    on_disk = sorted(
        p.name for p in font_dir.iterdir() if p.is_file()
    ) if font_dir.is_dir() else []

    referenced_names = sorted(referenced)
    return {
        "referenced_in_code": dict(
            sorted(referenced.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "declared_in_pubspec": declared,
        "files_on_disk": on_disk,
        # The finding, computed rather than asserted: a family the code asks for
        # that the build never declared cannot load, so Flutter falls back
        # without erroring and every screen renders in the default face.
        "referenced_but_not_declared": [
            name for name in referenced_names if name not in declared
        ],
        "declared_but_not_referenced": [
            name for name in declared if name not in referenced
        ],
    }


def render(data: dict) -> str:
    """The survey as text, for reading. `--json` is what the brief gets."""
    inv = data["inventory"]
    lines = [
        f"UI survey — {data['app_root']}",
        "",
        f"  UI files ({', '.join(inv['directories_walked'])})  "
        f"{inv['ui_files']} files, {inv['ui_lines']:,} lines",
        f"  repo-wide .dart                       "
        f"{inv['dart_files_repo_wide']} files, {inv['dart_lines_repo_wide']:,} lines",
        "",
        "  pattern                     UI     repo-wide",
    ]
    for name, _ in PATTERNS:
        lines.append(
            f"    {name:<24} {data['counts']['ui'][name]:>6} {data['counts']['repo_wide'][name]:>10}"
        )

    fonts = data["fonts"]
    lines += ["", "  fonts"]
    lines.append(f"    referenced in code    {', '.join(fonts['referenced_in_code']) or '(none)'}")
    lines.append(f"    declared in pubspec   {', '.join(fonts['declared_in_pubspec']) or '(none)'}")
    lines.append(f"    files on disk         {', '.join(fonts['files_on_disk']) or '(none)'}")
    if fonts["referenced_but_not_declared"]:
        lines.append(
            f"    CANNOT LOAD           {', '.join(fonts['referenced_but_not_declared'])}"
            f"  <- renders as a silent fallback"
        )

    members = list(data["theme_members"].items())[:15]
    if members:
        lines += ["", "  most-referenced AppTheme members"]
        lines += [f"    {name:<28} {count:>5}" for name, count in members]

    for name, _ in PATTERNS:
        top = data["rankings"][name][:5]
        if top:
            lines += ["", f"  top files — {name}"]
            lines += [f"    {e['count']:>5}  {e['path']}" for e in top]

    if data["problems"]:
        lines += ["", "  PROBLEMS"]
        lines += [f"    - {p}" for p in data["problems"]]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app_root", type=Path, help="the Flutter app's root directory")
    parser.add_argument("--json", action="store_true", help="emit JSON rather than text")
    parser.add_argument("--out", type=Path, default=None, help="write to this file too")
    args = parser.parse_args()

    root = args.app_root.expanduser().resolve()
    if not root.is_dir():
        print(f"{root} is not a directory", file=sys.stderr)
        return 2

    data = survey(root)
    payload = json.dumps(data, indent=2) if args.json else render(data)
    print(payload)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"\nwritten to {args.out}", file=sys.stderr)

    # Non-zero when the walk found nothing to measure, so a wrong path in a
    # script fails rather than producing a confident empty survey.
    return 1 if data["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
