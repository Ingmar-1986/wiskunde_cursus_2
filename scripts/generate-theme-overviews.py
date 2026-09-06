#!/usr/bin/env python3
r"""
Genereert automatisch een hoofdstukoverzicht voor ieder thema
in een Ximera-module.

De thema's worden bepaald door:

    \FVDpart{Titel van het thema}

Alle \activity{...}-commando's tot aan de volgende \FVDpart
worden bij dat thema geplaatst.

Het gegenereerde overzicht wordt vlak vóór de eerste
\begin{themaintro} van het thema ingevoegd.

Wanneer een thema geen themaintro bevat, wordt het overzicht
vlak vóór de eerste activiteit geplaatst. Wanneer ook die
ontbreekt, wordt het overzicht aan het einde van het thema
ingevoegd.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


BEGIN_MARKER = "% BEGIN AUTO THEME OVERVIEW"
END_MARKER = "% END AUTO THEME OVERVIEW"

PART_PATTERN = re.compile(r"\\FVDpart\s*\{")
ACTIVITY_PATTERN = re.compile(r"\\activity\s*\{")
THEME_INTRO_PATTERN = re.compile(r"\\begin\s*\{\s*themaintro\s*\}")

ACTIVITY_COMMAND_PATTERN = re.compile(
    r"\\activity\s*\{(?P<activity>[^{}]*)\}"
)

CHAPTERPAIR_COMMAND_PATTERN = re.compile(
    r"\\FVDchapterpair\s*"
    r"\{(?P<theory>[^{}]*)\}\s*"
    r"\{(?P<exercises>[^{}]*)\}"
)


@dataclass
class Activity:
    line_number: int
    path: str
    title: str


@dataclass
class Theme:
    title: str
    part_line: int
    next_part_line: int
    activities: list[Activity]


def remove_latex_comments(text: str) -> str:
    """Verwijdert LaTeX-commentaar, maar bewaart escaped procenttekens."""

    cleaned_lines: list[str] = []

    for line in text.splitlines():
        result: list[str] = []
        index = 0

        while index < len(line):
            character = line[index]

            if character == "%":
                backslashes = 0
                check_index = index - 1

                while check_index >= 0 and line[check_index] == "\\":
                    backslashes += 1
                    check_index -= 1

                if backslashes % 2 == 0:
                    break

            result.append(character)
            index += 1

        cleaned_lines.append("".join(result))

    return "\n".join(cleaned_lines)


def extract_braced_argument(
    text: str,
    command_start: int,
) -> tuple[str, int] | None:
    """Leest een accolade-argument, inclusief geneste accolades."""

    opening_brace = text.find("{", command_start)

    if opening_brace == -1:
        return None

    depth = 0

    for index in range(opening_brace, len(text)):
        character = text[index]

        if character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                return text[opening_brace + 1:index], index + 1

    return None


def extract_argument_from_line(
    line: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Haalt het eerste accolade-argument uit een regel."""

    uncommented = remove_latex_comments(line)
    match = pattern.search(uncommented)

    if not match:
        return None

    result = extract_braced_argument(uncommented, match.start())

    if result is None:
        return None

    argument, _ = result
    return argument.strip()


def extract_command_argument(text: str, command: str) -> str | None:
    """Haalt het eerste argument van een LaTeX-commando op."""

    cleaned = remove_latex_comments(text)
    pattern = re.compile(rf"\\{re.escape(command)}\s*\{{")
    match = pattern.search(cleaned)

    if not match:
        return None

    result = extract_braced_argument(cleaned, match.start())

    if result is None:
        return None

    argument, _ = result
    return argument.strip()


def clean_title(title: str) -> str:
    """Normaliseert een hoofdstuktitel zonder nuttige LaTeX te verwijderen."""

    title = re.sub(r"\s+", " ", title).strip()

    bold_match = re.fullmatch(
        r"\\textbf\s*\{(.+)\}",
        title,
        flags=re.DOTALL,
    )

    if bold_match:
        title = bold_match.group(1).strip()

    return title


def remove_generated_blocks(lines: list[str]) -> list[str]:
    """Verwijdert eerder gegenereerde themablokken."""

    output: list[str] = []
    inside_block = False

    for line in lines:
        stripped = line.strip()

        if stripped == BEGIN_MARKER:
            inside_block = True
            continue

        if stripped == END_MARKER:
            inside_block = False
            continue

        if not inside_block:
            output.append(line)

    if inside_block:
        raise ValueError(
            f"Er staat een '{BEGIN_MARKER}' zonder '{END_MARKER}'."
        )

    return output


def resolve_activity_file(index_file: Path, activity_path: str) -> Path | None:
    """Zoekt het LaTeX-bestand van een activiteit."""

    activity_path = activity_path.strip()
    base_path = index_file.parent / activity_path

    candidates = [
        base_path,
        base_path.with_suffix(".tex"),
        base_path / "index.tex",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def fallback_title(activity_path: str) -> str:
    """Maakt een leesbare titel van het activiteitpad."""

    name = Path(activity_path).name
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip() or activity_path


def read_activity_title(index_file: Path, activity_path: str) -> str:
    """Leest de titel van een activiteitbestand."""

    activity_file = resolve_activity_file(index_file, activity_path)

    if activity_file is None:
        print(
            f"Waarschuwing: activiteitbestand niet gevonden: {activity_path}",
            file=sys.stderr,
        )
        return fallback_title(activity_path)

    source = activity_file.read_text(
        encoding="utf-8",
        errors="replace",
    )

    title = extract_command_argument(source, "title")

    if title is None:
        title = extract_command_argument(source, "fvdtitle")

    if title is None:
        print(
            f"Waarschuwing: geen titel gevonden in {activity_file}",
            file=sys.stderr,
        )
        return fallback_title(activity_path)

    return clean_title(title)


def find_themes(lines: list[str], index_file: Path) -> list[Theme]:
    """Zoekt thema's en leest hun activiteiten."""

    part_locations: list[tuple[int, str]] = []

    for line_number, line in enumerate(lines):
        title = extract_argument_from_line(line, PART_PATTERN)

        if title is not None:
            part_locations.append((line_number, clean_title(title)))

    themes: list[Theme] = []

    for part_index, (part_line, part_title) in enumerate(part_locations):
        if part_index + 1 < len(part_locations):
            next_part_line = part_locations[part_index + 1][0]
        else:
            next_part_line = len(lines)

        activities: list[Activity] = []

        theme_start_line = part_line + 1
        theme_text = "\n".join(lines[theme_start_line:next_part_line])

        found_activities: list[tuple[int, str]] = []

        # Gewone \activity{...}
        for match in ACTIVITY_COMMAND_PATTERN.finditer(theme_text):
            activity_path = match.group("activity").strip()

            line_number = (
                theme_start_line
                + theme_text.count("\n", 0, match.start())
            )

            found_activities.append(
                (line_number, activity_path)
            )

        # \FVDchapterpair{theorie}{oefeningen}
        # Voor het thema-overzicht telt alleen het theoriehoofdstuk.
        for match in CHAPTERPAIR_COMMAND_PATTERN.finditer(theme_text):
            activity_path = match.group("theory").strip()

            line_number = (
                theme_start_line
                + theme_text.count("\n", 0, match.start())
            )

            found_activities.append(
                (line_number, activity_path)
            )

        # Bronvolgorde behouden
        found_activities.sort(key=lambda item: item[0])

        for line_number, activity_path in found_activities:
            activities.append(
                Activity(
                    line_number=line_number,
                    path=activity_path,
                    title=read_activity_title(index_file, activity_path),
                )
            )

        themes.append(
            Theme(
                title=part_title,
                part_line=part_line,
                next_part_line=next_part_line,
                activities=activities,
            )
        )

    return themes


def build_overview(theme: Theme) -> list[str]:
    """Bouwt het gegenereerde LaTeX-blok voor één thema."""

    lines = [
        BEGIN_MARKER,
        r"\begin{hoofdstukoverzicht}",
    ]

    if theme.activities:
        for chapter_number, activity in enumerate(theme.activities, start=1):
            lines.append(
                r"  \FVDthemechaptertile"
                f"{{{chapter_number}}}"
                f"{{{activity.title}}}"
            )
    else:
        lines.append(r"  \FVDthemeoverviewempty")

    lines.extend(
        [
            r"\end{hoofdstukoverzicht}",
            END_MARKER,
        ]
    )

    return lines


def find_theme_intro_line(lines: list[str], theme: Theme) -> int | None:
    """Zoekt de eerste \begin{themaintro} binnen het thema."""

    for line_number in range(theme.part_line + 1, theme.next_part_line):
        uncommented = remove_latex_comments(lines[line_number])

        if THEME_INTRO_PATTERN.search(uncommented):
            return line_number

    return None


def insert_overviews(lines: list[str], themes: list[Theme]) -> list[str]:
    """
    Voegt ieder overzicht vlak vóór de eerste
    \begin{themaintro} van het thema in.

    Terugval:
    1. vóór de eerste activiteit;
    2. aan het einde van het thema.
    """

    insertions: dict[int, list[str]] = {}

    for theme in themes:
        insertion_line = find_theme_intro_line(lines, theme)

        if insertion_line is None and theme.activities:
            insertion_line = theme.activities[0].line_number

        if insertion_line is None:
            insertion_line = theme.next_part_line

        insertions.setdefault(insertion_line, []).extend(build_overview(theme))

    output: list[str] = []

    for line_number, line in enumerate(lines):
        if line_number in insertions:
            if output and output[-1].strip():
                output.append("")

            output.extend(insertions[line_number])
            output.append("")

        output.append(line)

    if len(lines) in insertions:
        if output and output[-1].strip():
            output.append("")

        output.extend(insertions[len(lines)])
        output.append("")

    return output


def generate(index_file: Path, create_backup: bool) -> None:
    """Genereert alle thema-overzichten."""

    if not index_file.is_file():
        raise FileNotFoundError(f"Indexbestand niet gevonden: {index_file}")

    original_text = index_file.read_text(encoding="utf-8")
    original_lines = original_text.splitlines()
    clean_lines = remove_generated_blocks(original_lines)

    themes = find_themes(clean_lines, index_file)

    if not themes:
        print(f"Geen \\FVDpart-commando's gevonden in {index_file}.")
        return

    generated_lines = insert_overviews(clean_lines, themes)
    generated_text = "\n".join(generated_lines).rstrip() + "\n"

    if create_backup:
        backup_file = index_file.with_suffix(index_file.suffix + ".bak")
        shutil.copy2(index_file, backup_file)
        print(f"Back-up gemaakt: {backup_file}")

    index_file.write_text(generated_text, encoding="utf-8")

    print(f"Thema-overzichten gegenereerd: {index_file}")
    print(f"Aantal thema's: {len(themes)}")

    for number, theme in enumerate(themes, start=1):
        chapter_count = len(theme.activities)
        suffix = "" if chapter_count == 1 else "ken"

        print(
            f"  Thema {number}: {theme.title} "
            f"({chapter_count} hoofdstuk{suffix})"
        )


def parse_arguments() -> argparse.Namespace:
    """Leest de argumenten van de opdrachtregel."""

    parser = argparse.ArgumentParser(
        description=(
            "Genereer automatisch een hoofdstukoverzicht "
            "voor ieder thema."
        )
    )

    parser.add_argument(
        "index_file",
        type=Path,
        help="Het index.tex-bestand van de module.",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Maak geen .bak-bestand.",
    )

    return parser.parse_args()


def main() -> int:
    """Startpunt van het script."""

    arguments = parse_arguments()

    try:
        generate(
            arguments.index_file.resolve(),
            create_backup=not arguments.no_backup,
        )
    except Exception as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())