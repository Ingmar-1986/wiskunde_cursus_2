#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# PROJECTROOT BEPALEN
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ============================================================
# ARGUMENT CONTROLEREN
# ============================================================

MODULE_DIR="${1:-}"

if [ -z "$MODULE_DIR" ]; then
    echo "Gebruik:"
    echo "bash scripts/generate-sidebar.sh modules/basiswiskunde"
    exit 1
fi

# Eventuele afsluitende slash verwijderen
MODULE_DIR="${MODULE_DIR%/}"

XOURSE_HTML="$MODULE_DIR/index.html"
SIDEBAR_OUTPUT="$MODULE_DIR/CourseSidebar.generated.html"

if [ ! -f "$XOURSE_HTML" ]; then
    echo "Fout: $XOURSE_HTML werd niet gevonden."
    exit 1
fi

# ============================================================
# MODULENAAM AFLEIDEN
# ============================================================

MODULE_NAME="$(basename "$MODULE_DIR")"

# basiswiskunde -> Basiswiskunde
# lineaire-functies -> Lineaire Functies
MODULE_TITLE="$(
    printf '%s' "$MODULE_NAME" |
    sed 's/_/ /g; s/-/ /g' |
    awk '{
        for (i = 1; i <= NF; i++) {
            $i = toupper(substr($i, 1, 1)) substr($i, 2)
        }
        print
    }'
)"

# ============================================================
# SIDEBAR GENEREREN MET PYTHON
# ============================================================

python3 - \
    "$XOURSE_HTML" \
    "$SIDEBAR_OUTPUT" \
    "$MODULE_TITLE" <<'PY'
from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


source_file = Path(sys.argv[1])
output_file = Path(sys.argv[2])
module_title = sys.argv[3]

document = source_file.read_text(encoding="utf-8")


# ============================================================
# HULPFUNCTIES
# ============================================================

TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)


def strip_html(value: str) -> str:
    """Verwijder HTML-tags en decodeer entiteiten."""
    value = TAG_PATTERN.sub("", value)
    return html.unescape(value).strip()


def normalize_href(raw_href: str) -> str:
    """
    Zet bijvoorbeeld:

    modules/basiswiskunde/breuken
    ./breuken
    breuken
    breuken.html

    om naar:

    breuken.html
    """

    parsed = urlparse(raw_href)
    path = parsed.path.rstrip("/")

    filename = Path(path).name

    if not filename:
        return "#"

    if not filename.endswith(".html"):
        filename += ".html"

    return filename


# ============================================================
# THEMA'S EN HOOFDSTUKKAARTEN VINDEN
# ============================================================

# Herkent de omgezette themahoofding:
#
# <div class="activity-card card-sectionheading card part" id="part1">
#   <div class="card-block">
#     <h4 class="card-title">Getallen en bewerkingen</h4>
#   </div>
# </div>
#
PART_PATTERN = re.compile(
    r"""
    <div
        (?=[^>]*\bclass=["'][^"']*\bpart\b[^"']*["'])
        (?=[^>]*\bclass=["'][^"']*\bcard-sectionheading\b[^"']*["'])
        [^>]*>
        .*?
        <h4
            [^>]*\bclass=["'][^"']*\bcard-title\b[^"']*["']
            [^>]*>
            (?P<title>.*?)
        </h4>
        .*?
    </div>
    \s*
    </div>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


# Herkent een Ximera-hoofdstukkaart:
#
# <a class='activity card '
#    href='modules/basiswiskunde/breuken'>
#     <h3>...</h3>
#     <h2>Machten en wortels</h2>
#     breuken
# </a>
#
CHAPTER_PATTERN = re.compile(
    r"""
    <a
        (?=[^>]*\bclass=["'][^"']*\bactivity\b[^"']*\bcard\b[^"']*["'])
        [^>]*\bhref=["'](?P<href>[^"']+)["']
        [^>]*>
        (?P<body>.*?)
    </a>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


CHAPTER_TITLE_PATTERN = re.compile(
    r"""
    <h2[^>]*>
        (?P<title>.*?)
    </h2>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


# ============================================================
# TOKENS IN DOCUMENTVOLGORDE VERZAMELEN
# ============================================================

tokens: list[tuple[int, str, re.Match[str]]] = []

for match in PART_PATTERN.finditer(document):
    tokens.append((match.start(), "part", match))

for match in CHAPTER_PATTERN.finditer(document):
    tokens.append((match.start(), "chapter", match))

tokens.sort(key=lambda item: item[0])


# ============================================================
# STRUCTUUR OPBOUWEN
# ============================================================

sections: list[dict[str, object]] = []
current_section: dict[str, object] | None = None

for _, token_type, match in tokens:

    if token_type == "part":
        title = strip_html(match.group("title"))

        if not title:
            continue

        current_section = {
            "title": title,
            "chapters": [],
        }

        sections.append(current_section)
        continue

    if token_type == "chapter":
        chapter_body = match.group("body")
        raw_href = match.group("href")

        title_match = CHAPTER_TITLE_PATTERN.search(chapter_body)

        if not title_match:
            print(
                f"Waarschuwing: geen <h2>-titel gevonden voor link {raw_href}",
                file=sys.stderr,
            )
            continue

        chapter_title = strip_html(title_match.group("title"))
        chapter_href = normalize_href(raw_href)

        if current_section is None:
            current_section = {
                "title": "Hoofdstukken",
                "chapters": [],
            }
            sections.append(current_section)

        chapters = current_section["chapters"]

        assert isinstance(chapters, list)

        chapters.append(
            {
                "title": chapter_title,
                "href": chapter_href,
            }
        )


# Lege thema's verwijderen
sections = [
    section
    for section in sections
    if isinstance(section.get("chapters"), list)
    and len(section["chapters"]) > 0
]


if not sections:
    print(
        "Fout: geen thema's of hoofdstukken gevonden in index.html.",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================
# HTML GENEREREN
# ============================================================

lines: list[str] = []

lines.append('<aside class="course-sidebar" id="courseSidebar">')
lines.append("")
lines.append('    <div class="sidebar-header">')
lines.append("        <div>")
lines.append(
    f'            <span class="sidebar-label">{html.escape(module_title)}</span>'
)
lines.append("            <h2>Cursusinhoud</h2>")
lines.append("        </div>")
lines.append("")
lines.append("        <button")
lines.append('            class="sidebar-close"')
lines.append('            id="sidebarClose"')
lines.append('            type="button"')
lines.append('            aria-label="Sluit cursusmenu"')
lines.append("        >")
lines.append("            ×")
lines.append("        </button>")
lines.append("    </div>")
lines.append("")
lines.append(
    '    <nav class="course-navigation" aria-label="Cursusinhoud">'
)
lines.append("")

for section_index, section in enumerate(sections, start=1):

    section_title = str(section["title"])
    chapters = section["chapters"]

    assert isinstance(chapters, list)

    lines.append('        <div class="course-section">')
    lines.append("")
    lines.append(
        '            <button class="course-section-toggle" type="button">'
    )
    lines.append(
        f'                <span class="section-number">{section_index}</span>'
    )
    lines.append(
        "                "
        f'<span class="section-name">{html.escape(section_title)}</span>'
    )
    lines.append(
        '                <span class="section-arrow">⌄</span>'
    )
    lines.append("            </button>")
    lines.append("")
    lines.append('            <div class="course-section-content">')

    for chapter_index, chapter in enumerate(chapters, start=1):

        chapter_title = str(chapter["title"])
        chapter_href = str(chapter["href"])
        chapter_number = f"{section_index}.{chapter_index}"

        lines.append(
            "                "
            f'<a href="{html.escape(chapter_href, quote=True)}">'
            f"{chapter_number} {html.escape(chapter_title)}"
            "</a>"
        )

    lines.append("            </div>")
    lines.append("")
    lines.append("        </div>")
    lines.append("")

lines.append("    </nav>")
lines.append("")
lines.append("</aside>")

output_file.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)


# ============================================================
# RESULTAAT TONEN
# ============================================================

chapter_count = sum(
    len(section["chapters"])
    for section in sections
)

print(f"Sidebar aangemaakt: {output_file}")
print(f"Aantal thema's: {len(sections)}")
print(f"Aantal hoofdstukken: {chapter_count}")
PY