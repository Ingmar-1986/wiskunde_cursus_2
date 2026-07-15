#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULE_DIR="${1:-}"

if [ -z "$MODULE_DIR" ]; then
    echo "Gebruik:"
    echo "bash scripts/generate-sidebar.sh modules/basiswiskunde"
    exit 1
fi

XOURSE_HTML="$MODULE_DIR/index.html"
SIDEBAR_OUTPUT="$MODULE_DIR/CourseSidebar.generated.html"

if [ ! -f "$XOURSE_HTML" ]; then
    echo "Fout: $XOURSE_HTML werd niet gevonden."
    exit 1
fi

MODULE_NAME="$(basename "$MODULE_DIR")"

# Mooie schrijfwijze:
# basiswiskunde -> Basiswiskunde
MODULE_TITLE="$(printf '%s' "$MODULE_NAME" | sed 's/_/ /g; s/-/ /g; s/\b\(.\)/\u\1/g')"

python3 - "$XOURSE_HTML" "$SIDEBAR_OUTPUT" "$MODULE_TITLE" <<'PY'
import html
import re
import sys
from pathlib import Path

source_file = Path(sys.argv[1])
output_file = Path(sys.argv[2])
module_title = sys.argv[3]

document = source_file.read_text(encoding="utf-8")

# We zoeken zowel:
# - de omgezette themahoofden
# - de hoofdstukkaarten
token_pattern = re.compile(
    r"""
    (
        <div
        [^>]*class=["'][^"']*
        activity-card\s+card-sectionheading\s+card\s+part
        [^"']*["']
        [^>]*>
        .*?
        </div>\s*</div>
    )
    |
    (
        <a
        [^>]*class=["'][^"']*activity\s+card[^"']*["']
        [^>]*href=["']([^"']+)["']
        [^>]*>
        .*?
        </a>
    )
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

part_title_pattern = re.compile(
    r'<h4[^>]*class=["\'][^"\']*card-title[^"\']*["\'][^>]*>(.*?)</h4>',
    re.IGNORECASE | re.DOTALL,
)

chapter_title_pattern = re.compile(
    r'<h2[^>]*>(.*?)</h2>',
    re.IGNORECASE | re.DOTALL,
)

tag_pattern = re.compile(r"<[^>]+>")

sections = []
current_section = None

for match in token_pattern.finditer(document):
    part_html = match.group(1)
    chapter_html = match.group(2)

    if part_html:
        title_match = part_title_pattern.search(part_html)

        if not title_match:
            continue

        title = tag_pattern.sub("", title_match.group(1))
        title = html.unescape(title).strip()

        current_section = {
            "title": title,
            "chapters": [],
        }

        sections.append(current_section)

    elif chapter_html:
        href = match.group(3)

        title_match = chapter_title_pattern.search(chapter_html)

        if not title_match:
            continue

        title = tag_pattern.sub("", title_match.group(1))
        title = html.unescape(title).strip()

        # Veiligheid: wanneer er nog geen part gevonden is
        if current_section is None:
            current_section = {
                "title": "Hoofdstukken",
                "chapters": [],
            }
            sections.append(current_section)

        current_section["chapters"].append({
            "title": title,
            "href": href,
        })

lines = []

lines.append('<aside class="course-sidebar" id="courseSidebar">')
lines.append('')
lines.append('    <div class="sidebar-header">')
lines.append('        <div>')
lines.append(f'            <span class="sidebar-label">{html.escape(module_title)}</span>')
lines.append('            <h2>Cursusinhoud</h2>')
lines.append('        </div>')
lines.append('')
lines.append('        <button')
lines.append('            class="sidebar-close"')
lines.append('            id="sidebarClose"')
lines.append('            type="button"')
lines.append('            aria-label="Sluit cursusmenu"')
lines.append('        >')
lines.append('            ×')
lines.append('        </button>')
lines.append('    </div>')
lines.append('')
lines.append('    <nav class="course-navigation" aria-label="Cursusinhoud">')
lines.append('')

for section_index, section in enumerate(sections, start=1):
    lines.append('        <div class="course-section">')
    lines.append('')
    lines.append('            <button class="course-section-toggle" type="button">')
    lines.append(f'                <span class="section-number">{section_index}</span>')
    lines.append(
        f'                <span class="section-name">{html.escape(section["title"])}</span>'
    )
    lines.append('                <span class="section-arrow">⌄</span>')
    lines.append('            </button>')
    lines.append('')
    lines.append('            <div class="course-section-content">')

    for chapter_index, chapter in enumerate(section["chapters"], start=1):
        chapter_number = f"{section_index}.{chapter_index}"

        lines.append(
            f'                <a href="{html.escape(chapter["href"], quote=True)}">'
            f'{chapter_number} {html.escape(chapter["title"])}</a>'
        )

    lines.append('            </div>')
    lines.append('')
    lines.append('        </div>')
    lines.append('')

lines.append('    </nav>')
lines.append('')
lines.append('</aside>')

output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"Sidebar aangemaakt: {output_file}")
print(f"Aantal thema's: {len(sections)}")
print(
    "Aantal hoofdstukken:",
    sum(len(section["chapters"]) for section in sections),
)
PY