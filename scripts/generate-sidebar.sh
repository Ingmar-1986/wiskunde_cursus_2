#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# Ximera – sidebar genereren
#
# Gebruik:
#   bash scripts/generate-sidebar.sh modules/basiswiskunde
#
# Zonder argument:
#   bash scripts/generate-sidebar.sh
#
# Dan wordt standaard modules/basiswiskunde gebruikt.
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODULE_RELATIVE="${1:-modules/basiswiskunde}"
MODULE_DIR="$PROJECT_ROOT/$MODULE_RELATIVE"

INDEX_FILE="$MODULE_DIR/index.tex"
TEMPLATE_FILE="$PROJECT_ROOT/assets/html/SidebarTemplate.html"
OUTPUT_FILE="$MODULE_DIR/CourseSidebar.generated.html"

echo
echo "Sidebar genereren"
echo "────────────────────────────────────────"
echo "Module:    $MODULE_RELATIVE"
echo "Index:     $INDEX_FILE"
echo "Template:  $TEMPLATE_FILE"
echo "Uitvoer:   $OUTPUT_FILE"
echo

if [[ ! -d "$MODULE_DIR" ]]; then
    echo "Fout: modulemap bestaat niet:"
    echo "  $MODULE_DIR"
    exit 1
fi

if [[ ! -f "$INDEX_FILE" ]]; then
    echo "Fout: index.tex niet gevonden:"
    echo "  $INDEX_FILE"
    exit 1
fi

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Fout: SidebarTemplate.html niet gevonden:"
    echo "  $TEMPLATE_FILE"
    exit 1
fi

python3 - "$INDEX_FILE" "$TEMPLATE_FILE" "$OUTPUT_FILE" "$MODULE_DIR" <<'PYTHON'
from __future__ import annotations

import html
import re
import sys
from pathlib import Path


# ============================================================
# Paden
# ============================================================

index_file = Path(sys.argv[1])
template_file = Path(sys.argv[2])
output_file = Path(sys.argv[3])
module_dir = Path(sys.argv[4])


# ============================================================
# Hulpfuncties
# ============================================================

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def remove_comments(source: str) -> str:
    """
    Verwijdert LaTeX-commentaar, maar behoudt escaped procenttekens: \%
    """
    cleaned_lines: list[str] = []

    for line in source.splitlines():
        result: list[str] = []
        escaped = False

        for character in line:
            if character == "%" and not escaped:
                break

            result.append(character)

            if character == "\\":
                escaped = not escaped
            else:
                escaped = False

        cleaned_lines.append("".join(result))

    return "\n".join(cleaned_lines)


def clean_latex_text(value: str) -> str:
    """
    Zet eenvoudige LaTeX-opmaak om naar leesbare platte tekst.
    Dit is voldoende voor titels in de sidebar.
    """
    value = value.strip()

    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\#": "#",
        r"\_": "_",
        r"\{": "{",
        r"\}": "}",
        "~": " ",
        "---": "—",
        "--": "–",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    # Veelgebruikte opmaakcommando's verwijderen,
    # maar de inhoud tussen accolades behouden.
    formatting_commands = (
        "textbf",
        "textit",
        "emph",
        "mathrm",
        "mathbf",
        "mathit",
        "textrm",
        "textsf",
        "texttt",
    )

    for command in formatting_commands:
        value = re.sub(
            rf"\\{command}\s*\{{([^{{}}]*)\}}",
            r"\1",
            value,
        )

    # Eenvoudige inline math-delimiters verwijderen.
    value = value.replace(r"\(", "").replace(r"\)", "")
    value = value.replace("$", "")

    # Resterende eenvoudige LaTeX-commando's verwijderen.
    value = re.sub(r"\\[a-zA-Z@]+\*?", "", value)

    # Losse accolades verwijderen.
    value = value.replace("{", "").replace("}", "")

    # Witruimte normaliseren.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_first_argument(source: str, command_names: tuple[str, ...]) -> str | None:
    """
    Zoekt het eerste argument van bijvoorbeeld:
        \title{Titel}
        \fvdtitle{Titel}

    Ondersteunt ook eenvoudige geneste accolades.
    """
    command_pattern = "|".join(re.escape(name) for name in command_names)

    match = re.search(
        rf"\\(?:{command_pattern})\s*\{{",
        source,
    )

    if not match:
        return None

    start = match.end()
    depth = 1
    position = start

    while position < len(source):
        character = source[position]

        if character == "\\":
            position += 2
            continue

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return source[start:position]

        position += 1

    return None


def resolve_activity_file(activity: str) -> Path | None:
    """
    Ondersteunt onder meer:

        \activity{rekenen}
        \activity{hoofdstukken/rekenen}
        \activity{rekenen.tex}
        \activity{rekenen/rekenen}

    Probeert enkele gebruikelijke Ximera-structuren.
    """
    activity = activity.strip()

    candidates: list[Path] = []

    activity_path = Path(activity)

    if activity_path.suffix == ".tex":
        candidates.append(module_dir / activity_path)
    else:
        candidates.extend(
            [
                module_dir / f"{activity}.tex",
                module_dir / activity / f"{activity_path.name}.tex",
                module_dir / activity / "index.tex",
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def activity_url(activity: str) -> str:
    """
    Maakt de HTML-link die bij een activity hoort.
    """
    activity = activity.strip().replace("\\", "/")

    if activity.endswith(".tex"):
        activity = activity[:-4]

    if activity.endswith("/index"):
        activity = activity[:-6]

    return f"{activity}.html"


def activity_fallback_title(activity: str) -> str:
    """
    Maakt van bijvoorbeeld wetenschappelijke_notatie:
        Wetenschappelijke notatie
    """
    name = Path(activity).stem
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()

    return name[:1].upper() + name[1:] if name else "Hoofdstuk"


def get_activity_title(activity: str) -> tuple[str, Path | None]:
    chapter_file = resolve_activity_file(activity)

    if chapter_file is None:
        return activity_fallback_title(activity), None

    source = remove_comments(read_text(chapter_file))

    title = extract_first_argument(
        source,
        (
            "title",
            "fvdtitle",
            "activitytitle",
            "chaptertitle",
        ),
    )

    if title:
        cleaned = clean_latex_text(title)

        if cleaned:
            return cleaned, chapter_file

    return activity_fallback_title(activity), chapter_file


def make_slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


# ============================================================
# index.tex analyseren
# ============================================================

index_source = remove_comments(read_text(index_file))

module_title_raw = extract_first_argument(
    index_source,
    (
        "fvdtitle",
        "title",
    ),
)

module_title = (
    clean_latex_text(module_title_raw)
    if module_title_raw
    else module_dir.name.replace("-", " ").replace("_", " ").title()
)

token_pattern = re.compile(
    r"""
    \\(?:FVDpart|part)\s*\{(?P<part>[^{}]*)\}
    |
    \\FVDchapterpair\s*
        \{(?P<pair_theory>[^{}]*)\}\s*
        \{(?P<pair_exercises>[^{}]*)\}
    |
    \\activity\s*\{(?P<activity>[^{}]*)\}
    """,
    re.VERBOSE,
)

sections: list[dict[str, object]] = []
current_section: dict[str, object] | None = None

for match in token_pattern.finditer(index_source):
    part_name = match.group("part")
    activity_name = match.group("activity")
    pair_theory = match.group("pair_theory")
    pair_exercises = match.group("pair_exercises")

    if part_name is not None:
        theme_title = clean_latex_text(part_name)

        current_section = {
            "title": theme_title,
            "activities": [],
        }

        sections.append(current_section)
        continue

    activities_to_add: list[str] = []

    if pair_theory is not None:
        theory = pair_theory.strip()
        exercises = (pair_exercises or "").strip()

        if theory:
            activities_to_add.append(theory)

        if exercises:
            activities_to_add.append(exercises)

    elif activity_name is not None:
        activity_name = activity_name.strip()

        # De #1 en #2 uit de definitie van \FVDchapterpair
        # zijn geen echte activities.
        if activity_name in {"#1", "#2"}:
            continue

        activities_to_add.append(activity_name)

    if not activities_to_add:
        continue

    # Activities vóór de eerste \part krijgen een neutrale sectie.
    if current_section is None:
        current_section = {
            "title": "Inleiding",
            "activities": [],
        }
        sections.append(current_section)

    current_section["activities"].extend(activities_to_add)

if not sections:
    raise SystemExit(
        "Fout: geen \\part{...} of \\activity{...} gevonden in index.tex."
    )


# ============================================================
# Sidebarinhoud genereren
# ============================================================

sidebar_sections: list[str] = []
total_chapters = 0
missing_files: list[str] = []

for theme_index, section in enumerate(sections, start=1):
    theme_title = str(section["title"])
    activities = list(section["activities"])

    if not activities:
        continue

    theme_slug = make_slug(theme_title) or f"thema-{theme_index}"
    section_id = f"course-section-{theme_index}-{theme_slug}"

    chapter_links: list[str] = []

    # De hoofdstuknummering begint per thema opnieuw bij 1.
    for chapter_index, activity in enumerate(activities, start=1):
        total_chapters += 1

        chapter_title, chapter_file = get_activity_title(activity)

        if chapter_file is None:
            missing_files.append(activity)

        number = f"{theme_index}.{chapter_index}"
        url = activity_url(activity)

        chapter_links.append(
            f"""\
        <a
            class="course-chapter-link"
            href="{html.escape(url, quote=True)}"
            data-chapter="{html.escape(activity, quote=True)}"
        >
            <span class="course-chapter-number">
                {html.escape(number)}
            </span>

            <span class="course-chapter-title">
                {html.escape(chapter_title)}
            </span>
        </a>"""
        )

    links_html = "\n\n".join(chapter_links)

    sidebar_sections.append(
        f"""\
<div
    class="course-section"
    data-theme="{theme_index}"
>

    <button
        class="course-section-toggle"
        type="button"
        aria-expanded="true"
        aria-controls="{html.escape(section_id, quote=True)}"
    >
        <span class="course-section-number">
            {theme_index}
        </span>

        <span class="course-section-title">
            {html.escape(theme_title)}
        </span>

        <span
            class="course-section-arrow"
            aria-hidden="true"
        >
            ▾
        </span>
    </button>

    <div
        class="course-section-content"
        id="{html.escape(section_id, quote=True)}"
    >
{links_html}
    </div>

</div>"""
    )

sidebar_content = "\n\n".join(sidebar_sections)


# ============================================================
# Template invullen
# ============================================================

template = read_text(template_file)

# Ondersteunt beide namen die in eerdere templates gebruikt werden.
template = template.replace("{{MODULE}}", html.escape(module_title))
template = template.replace("{{MODULE_TITLE}}", html.escape(module_title))
template = template.replace("{{SIDEBAR_CONTENT}}", sidebar_content)

remaining_placeholders = sorted(
    set(re.findall(r"\{\{[A-Z0-9_]+\}\}", template))
)

if remaining_placeholders:
    print(
        "Waarschuwing: niet-ingevulde placeholders in SidebarTemplate.html:"
    )

    for placeholder in remaining_placeholders:
        print(f"  - {placeholder}")


# ============================================================
# Bestand schrijven
# ============================================================

generated_notice = """\
<!--
    AUTOMATISCH GEGENEREERD BESTAND

    Dit bestand wordt opgebouwd door:
        scripts/generate-sidebar.sh

    Bewerk niet dit bestand, maar:
        assets/html/SidebarTemplate.html
        en modules/.../index.tex
-->

"""

output_file.write_text(
    generated_notice + template.strip() + "\n",
    encoding="utf-8",
)

print(f"Module:       {module_title}")
print(f"Thema's:      {len(sidebar_sections)}")
print(f"Hoofdstukken: {total_chapters}")
print(f"Geschreven:   {output_file}")

if missing_files:
    print()
    print("Waarschuwing: voor deze activities werd geen TeX-bestand gevonden:")

    for activity in missing_files:
        print(f"  - {activity}")

    print("De bestandsnaam werd daarom als voorlopige titel gebruikt.")
PYTHON

echo
echo "Sidebar succesvol gegenereerd."
echo