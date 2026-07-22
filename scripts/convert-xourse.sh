#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULE_DIR="${1:-}"

if [[ -z "$MODULE_DIR" ]]; then
    echo "Gebruik: $0 modules/naam-van-module"
    exit 1
fi

MODULE_DIR="${MODULE_DIR%/}"

XOURSE_HTML="$MODULE_DIR/index.html"

XOURSE_SOURCE="$MODULE_DIR/index.online.html"

if [[ ! -f "$XOURSE_SOURCE" ]]; then
    echo "Fout: schone Ximera-bron ontbreekt: $XOURSE_SOURCE"
    exit 1
fi

cp "$XOURSE_SOURCE" "$XOURSE_HTML"



ASSETS_DIR="assets"
HTML_DIR="$ASSETS_DIR/html"
CSS_DIR="$ASSETS_DIR/css"
JS_DIR="$ASSETS_DIR/js"

HEADER_FILE="$HTML_DIR/Header.html"
FOOTER_FILE="$HTML_DIR/Footer.html"
COURSE_CARD_FILE="$HTML_DIR/CourseCard.html"

HEADER_FOOTER_CSS="../../assets/css/Header_Footer.css"
MODULE_CSS="../../assets/css/ModuleLayout.css"
COURSE_CARD_CSS="../../assets/css/CourseCard.css"
THEME_SCRIPT="../../assets/js/theme-toggle.js"

# ============================================================
# CONTROLES
# ============================================================

required_files=(
    "$XOURSE_HTML"
    "$HEADER_FILE"
    "$FOOTER_FILE"
    "$COURSE_CARD_FILE"
    "$CSS_DIR/Header_Footer.css"
    "$CSS_DIR/ModuleLayout.css"
)

for required_file in "${required_files[@]}"; do
    if [[ ! -f "$required_file" ]]; then
        echo "Fout: $required_file werd niet gevonden."
        exit 1
    fi
done

echo
echo "Moduleoverzicht verwerken"
echo "────────────────────────────────────────"
echo "Bestand: $XOURSE_HTML"
echo

# ============================================================
# OUDE INJECTIES VERWIJDEREN
# ============================================================
#
# Hierdoor kan het script veilig opnieuw uitgevoerd worden.
# De ruwe Ximera-inhoud blijft behouden.
#

perl -0pi -e '
    s{
        \s*<!--\s*XIMERA-HEADER-START\s*-->.*?
        <!--\s*XIMERA-HEADER-END\s*-->\s*
    }{}gsx;

    s{
        \s*<!--\s*XIMERA-INTRO-START\s*-->.*?
        <!--\s*XIMERA-INTRO-END\s*-->\s*
    }{}gsx;

    s{
        \s*<!--\s*XIMERA-FOOTER-START\s*-->.*?
        <!--\s*XIMERA-FOOTER-END\s*-->\s*
    }{}gsx;
' "$XOURSE_HTML"

# ============================================================
# CSS TOEVOEGEN
# ============================================================

add_stylesheet() {
    local stylesheet="$1"

    if ! grep -Fq "$stylesheet" "$XOURSE_HTML"; then
        sed -i \
            "s#</head>#  <link href='$stylesheet' media='screen' rel='stylesheet' />\n</head>#" \
            "$XOURSE_HTML"
    fi
}

add_stylesheet "$HEADER_FOOTER_CSS"
add_stylesheet "$MODULE_CSS"

# CourseCard.css alleen toevoegen wanneer het bestand bestaat.
if [[ -f "$CSS_DIR/CourseCard.css" ]]; then
    add_stylesheet "$COURSE_CARD_CSS"
fi

# ============================================================
# HEADER TOEVOEGEN
# ============================================================

sed -i \
    's#<body[^>]*>#&\
<!-- XIMERA-HEADER-START -->\
<!-- HEADER-PLACEHOLDER -->\
<!-- XIMERA-HEADER-END -->#' \
    "$XOURSE_HTML"

sed -i \
    "/<!-- HEADER-PLACEHOLDER -->/r $HEADER_FILE" \
    "$XOURSE_HTML"

sed -i \
    '/<!-- HEADER-PLACEHOLDER -->/d' \
    "$XOURSE_HTML"

# ============================================================
# PLACEHOLDERS IN HEADER VERVANGEN
# ============================================================

MODULE_NAME="$(basename "$MODULE_DIR")"

case "$MODULE_NAME" in
    basiswiskunde)
        MODULE_TITLE="Basiswiskunde"
        ;;
    *)
        MODULE_TITLE="${MODULE_NAME//-/ }"
        MODULE_TITLE="${MODULE_TITLE//_/ }"
        MODULE_TITLE="$(printf '%s' "$MODULE_TITLE" |
            sed -E 's/(^| )[a-z]/\U&/g')"
        ;;
esac

sed -i \
    "s#{{MODULE_TITLE}}#$MODULE_TITLE#g;
     s#{{MODULE}}#$MODULE_TITLE#g;
     s#{{CHAPTER_TITLE}}##g;
     s#{{CHAPTER_NUMBER}}##g;
     s#{{CHAPTER_LOCAL_NUMBER}}##g;
     s#{{THEME}}##g;
     s#{{THEME_NUMBER}}##g;
     s#{{ABSTRACT}}##g;
     s#{{ASSET_PREFIX}}#../../assets#g" \
    "$XOURSE_HTML"

# ============================================================
# MODULEINTRO RECHTSTREEKS GENEREREN
# ============================================================

MODULE_INTRO=$(cat <<EOF
<section class="module-overview-intro">
    <div class="module-overview-intro__content">
        <span class="module-overview-intro__eyebrow">
            $MODULE_TITLE
        </span>

        <h1 class="module-overview-intro__title">
            Cursusinhoud
        </h1>

        <p class="module-overview-intro__description">
            Kies hieronder een thema en open het hoofdstuk waarmee je wilt starten.
        </p>
    </div>
</section>
EOF
)

INTRO_TEMP_FILE="$(mktemp)"

printf '%s\n' "$MODULE_INTRO" > "$INTRO_TEMP_FILE"

sed -i \
    '/<!-- XIMERA-HEADER-END -->/a\
<!-- XIMERA-INTRO-START -->\
<!-- INTRO-PLACEHOLDER -->\
<!-- XIMERA-INTRO-END -->' \
    "$XOURSE_HTML"

sed -i \
    "/<!-- INTRO-PLACEHOLDER -->/r $INTRO_TEMP_FILE" \
    "$XOURSE_HTML"

sed -i \
    '/<!-- INTRO-PLACEHOLDER -->/d' \
    "$XOURSE_HTML"

rm -f "$INTRO_TEMP_FILE"

# ============================================================
# THEMA'S EN HOOFDSTUKKAARTEN OPBOUWEN
# ============================================================

MODULE_DIR="$MODULE_DIR" \
XOURSE_HTML="$XOURSE_HTML" \
COURSE_CARD_FILE="$COURSE_CARD_FILE" \
python - <<'PY'
from __future__ import annotations

import html
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


module_dir = Path(os.environ["MODULE_DIR"])
html_file = Path(os.environ["XOURSE_HTML"])
card_template_file = Path(os.environ["COURSE_CARD_FILE"])

source = html_file.read_text(encoding="utf-8")
card_template = card_template_file.read_text(encoding="utf-8")

soup = BeautifulSoup(source, "lxml")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def remove_latex_comments(source: str) -> str:
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


def extract_braced_argument(
    source: str,
    command_names: tuple[str, ...],
) -> str | None:
    command_pattern = "|".join(
        re.escape(name)
        for name in command_names
    )

    match = re.search(
        rf"\\(?:{command_pattern})\s*\{{",
        source,
    )

    if match is None:
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


def extract_environment(
    source: str,
    environment: str,
) -> str | None:
    match = re.search(
        rf"\\begin\s*\{{{re.escape(environment)}\}}"
        rf"(?P<content>.*?)"
        rf"\\end\s*\{{{re.escape(environment)}\}}",
        source,
        re.DOTALL,
    )

    if match is None:
        return None

    return match.group("content").strip()


def clean_latex_text(value: str) -> str:
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\#": "#",
        r"\_": "_",
        r"\ldots": "…",
        r"\dots": "…",
        "~": " ",
        "---": "—",
        "--": "–",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

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

    previous = None

    while previous != value:
        previous = value

        for command in formatting_commands:
            value = re.sub(
                rf"\\{command}\s*\{{([^{{}}]*)\}}",
                r"\1",
                value,
            )

    value = re.sub(
        r"\\[a-zA-Z@]+\*?",
        "",
        value,
    )

    value = value.replace("{", "").replace("}", "")
    value = value.replace("$", "")

    return clean_text(value)


def resolve_activity_tex(
    module_dir: Path,
    activity: str,
) -> Path | None:
    activity = activity.strip().replace("\\", "/")
    activity_path = Path(activity)

    if activity_path.suffix == ".tex":
        candidates = [
            module_dir / activity_path,
        ]
    else:
        candidates = [
            module_dir / f"{activity}.tex",
            module_dir / activity / f"{activity_path.name}.tex",
            module_dir / activity / "index.tex",
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def read_chapter_metadata(
    module_dir: Path,
    activity: str,
) -> tuple[str, str]:
    tex_file = resolve_activity_tex(
        module_dir,
        activity,
    )

    fallback_title = (
        Path(activity)
        .name
        .replace("-", " ")
        .replace("_", " ")
        .capitalize()
    )

    if tex_file is None:
        return fallback_title, ""

    source = remove_latex_comments(
        tex_file.read_text(encoding="utf-8")
    )

    title_raw = extract_braced_argument(
        source,
        (
            "title",
            "fvdtitle",
            "activitytitle",
            "chaptertitle",
        ),
    )

    title = (
        clean_latex_text(title_raw)
        if title_raw
        else fallback_title
    )

    abstract_raw = extract_environment(
        source,
        "abstract",
    )

    if abstract_raw is None:
        abstract_raw = extract_braced_argument(
            source,
            (
                "abstract",
                "fvdabstract",
                "chapterabstract",
            ),
        )

    abstract = (
        clean_latex_text(abstract_raw)
        if abstract_raw
        else ""
    )

    return title, abstract   


def render_card(
    *,
    url: str,
    number: str,
    title: str,
    abstract: str,
) -> list[Tag | NavigableString]:
    rendered = card_template

    replacements = {
        "{{URL}}": html.escape(url, quote=True),
        "{{CHAPTER_NUMBER}}": html.escape(number),
        "{{TITLE}}": html.escape(title),
        "{{ABSTRACT}}": html.escape(abstract),
    }

    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    fragment = BeautifulSoup(rendered, "html.parser")
    return list(fragment.contents)


theme_headers = list(soup.select("h1.card.part"))

for theme_index, theme_header in enumerate(theme_headers, start=1):
    theme_title = clean_text(
        theme_header.get_text(" ", strip=True)
    )

    # Alle knopen verzamelen tot het volgende thema.
    theme_nodes: list[Tag | NavigableString] = []
    current = theme_header.next_sibling

    while current is not None:
        next_node = current.next_sibling

        if (
            isinstance(current, Tag)
            and current.name == "h1"
            and "part" in current.get("class", [])
        ):
            break

        theme_nodes.append(current)
        current = next_node

    activity_links: list[Tag] = []

    for node in theme_nodes:
        if isinstance(node, Tag):
            activity_links.extend(
                node.select("a.activity.card")
            )

    details = soup.new_tag("details")
    details["class"] = ["course-theme"]

    # Eerste thema standaard open.
    if theme_index == 1:
        details["open"] = ""

    summary = soup.new_tag("summary")
    summary["class"] = ["course-theme__summary"]

    summary_main = soup.new_tag("span")
    summary_main["class"] = ["course-theme__summary-main"]

    badge = soup.new_tag("span")
    badge["class"] = ["course-theme__badge"]
    badge.string = f"Thema {theme_index}"

    text_container = soup.new_tag("span")
    text_container["class"] = ["course-theme__text"]

    title = soup.new_tag("span")
    title["class"] = ["course-theme__title"]
    title.string = theme_title

    count = soup.new_tag("span")
    count["class"] = ["course-theme__count"]

    chapter_count = len(activity_links)
    count.string = (
        f"{chapter_count} hoofdstuk"
        if chapter_count == 1
        else f"{chapter_count} hoofdstukken"
    )

    text_container.append(title)
    text_container.append(count)

    summary_main.append(badge)
    summary_main.append(text_container)

    chevron = soup.new_tag("span")
    chevron["class"] = ["course-theme__chevron"]
    chevron["aria-hidden"] = "true"
    chevron.string = "⌄"

    summary.append(summary_main)
    summary.append(chevron)

    card_grid = soup.new_tag("div")
    card_grid["class"] = ["course-theme-cards"]

    for chapter_index, link in enumerate(
        activity_links,
        start=1,
    ):
        href = str(link.get("href", "")).strip()

        activity = re.sub(
            r"(?:\.html)+$",
            "",
            href.rstrip("/"),
            flags=re.IGNORECASE,
        )

        activity = Path(activity).name

        chapter_title, abstract = read_chapter_metadata(
            module_dir,
            activity,
        )

        # Verwijder de moduletitel achteraan, indien aanwezig.
        chapter_title = re.sub(
            r"\s*[–—-]\s*Basiswiskunde\s*$",
            "",
            chapter_title,
            flags=re.IGNORECASE,
        )

        href_name = f"{activity}.html"
        chapter_number = str(chapter_index)

        for card_node in render_card(
            url=href_name,
            number=chapter_number,
            title=chapter_title,
            abstract=abstract,
        ):
            card_grid.append(card_node)

    details.append(summary)
    details.append(card_grid)

    # Nieuw thema vóór het oorspronkelijke h1 plaatsen.
    theme_header.insert_before(details)

    # Originele Ximera-inhoud verwijderen.
    theme_header.decompose()

    for node in theme_nodes:
        if isinstance(node, Tag):
            node.decompose()
        elif isinstance(node, NavigableString):
            node.extract()


html_file.write_text(
    str(soup) + "\n",
    encoding="utf-8",
)
PY
# ============================================================
# DUBBELE ABSTRACTS VERWIJDEREN
# ============================================================

perl -0pi -e '
    s{
        <div class='\''abstract'\''>
        .*?
        </div>
    }{}gsx;
' "$XOURSE_HTML"



# ============================================================
# FOOTER TOEVOEGEN
# ============================================================

sed -i \
    '/<\/body>/i\
<div class="course-footer-clear"></div>\
<!-- XIMERA-FOOTER-START -->\
<!-- FOOTER-PLACEHOLDER -->\
<!-- XIMERA-FOOTER-END -->' \
    "$XOURSE_HTML"

sed -i \
    "/<!-- FOOTER-PLACEHOLDER -->/r $FOOTER_FILE" \
    "$XOURSE_HTML"

sed -i \
    '/<!-- FOOTER-PLACEHOLDER -->/d' \
    "$XOURSE_HTML"

# Ook in de footer de algemene placeholders vervangen.
sed -i \
    "s#{{MODULE_TITLE}}#$MODULE_TITLE#g;
     s#{{MODULE}}#$MODULE_TITLE#g;
     s#{{CHAPTER_TITLE}}##g;
     s#{{CHAPTER_NUMBER}}##g;
     s#{{CHAPTER_LOCAL_NUMBER}}##g;
     s#{{THEME}}##g;
     s#{{THEME_NUMBER}}##g;
     s#{{ABSTRACT}}##g;
     s#{{ASSET_PREFIX}}#../../assets#g" \
    "$XOURSE_HTML"

# ============================================================
# JAVASCRIPT TOEVOEGEN
# ============================================================

if [[ -f "$JS_DIR/theme-toggle.js" ]]; then
    if ! grep -Fq "$THEME_SCRIPT" "$XOURSE_HTML"; then
        sed -i \
            "s#</body>#  <script src='$THEME_SCRIPT'></script>\n</body>#" \
            "$XOURSE_HTML"
    fi
fi

echo
echo "Moduleoverzicht succesvol verwerkt:"
echo "  $XOURSE_HTML"
echo