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

sudo rm -f "$XOURSE_HTML"
cp "$XOURSE_SOURCE" "$XOURSE_HTML"



ASSETS_DIR="assets"
HTML_DIR="$ASSETS_DIR/html"
CSS_DIR="$ASSETS_DIR/css"
JS_DIR="$ASSETS_DIR/js"

HEADER_FILE="$HTML_DIR/Header.html"
FOOTER_FILE="$HTML_DIR/Footer.html"
COURSE_CARD_FILE="$HTML_DIR/CourseCard.html"

BASE_CSS="../../assets/css/base.css"
GLOBAL_CSS="../../assets/css/global.css"
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

add_stylesheet "$BASE_CSS"
add_stylesheet "$GLOBAL_CSS"
add_stylesheet "$HEADER_FOOTER_CSS"
add_stylesheet "$MODULE_CSS"

# CourseCard.css alleen toevoegen wanneer het bestand bestaat.
if [[ -f "$CSS_DIR/CourseCard.css" ]]; then
    add_stylesheet "$COURSE_CARD_CSS"
fi

# Compacte hoofdstukkaarten afdwingen.
# Dit voorkomt dat één kaart de volledige hoogte van het themablok inneemt.
if ! grep -Fq "FVD-COMPACT-COURSE-CARDS" "$XOURSE_HTML"; then
    sed -i \
        "s#</head>#  <style id='FVD-COMPACT-COURSE-CARDS'>\n\
.course-theme-cards {\n\
    display: grid;\n\
    grid-template-columns: repeat(auto-fit, minmax(280px, 420px));\n\
    align-items: start;\n\
    align-content: start;\n\
    grid-auto-rows: auto;\n\
    gap: 1.25rem;\n\
}\n\
.course-card {\n\
    height: auto !important;\n\
    min-height: 0 !important;\n\
    align-self: start;\n\
}\n\
.course-card-link {\n\
    display: flex;\n\
    flex-direction: column;\n\
    height: auto !important;\n\
    min-height: 0 !important;\n\
    padding: 1.25rem;\n\
}\n\
.course-card-abstract {\n\
    margin: 0.9rem 0 1.1rem;\n\
    line-height: 1.55;\n\
}\n\
.course-card-footer {\n\
    margin-top: auto;\n\
}\n\
</style>\n</head>#" \
        "$XOURSE_HTML"
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
# THEMA'S EN HOOFDSTUKKAARTEN OPBOUWEN
# ============================================================

MODULE_DIR="$MODULE_DIR" \
XOURSE_HTML="$XOURSE_HTML" \
COURSE_CARD_FILE="$COURSE_CARD_FILE" \
python3 - <<'PY'
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
        else (
            "Open dit hoofdstuk om de leerstof, voorbeelden "
            "en oefeningen te bekijken."
        )
    )

    return title, abstract   


def render_card(
    url: str,
    number: str,
    title: str,
    abstract: str,
    exercise_url: str | None = None,
) -> list[Tag | NavigableString]:
    """
    Render één geldige hoofdstukkaart.

    Wanneer CourseCard.html onvolledig of fout afgesloten is,
    wordt automatisch een veilige standaardkaart opgebouwd.
    """

    rendered = card_template

    if exercise_url:
        exercise_button = (
            '<a href="'
            + html.escape(exercise_url, quote=True)
            + '" class="course-card-button course-card-button--exercise">'
            + 'Oefeningen →'
            + '</a>'
        )
    else:
        exercise_button = ""

    replacements = {
        "{{URL}}": html.escape(url, quote=True),
        "{{CHAPTER_NUMBER}}": html.escape(number),
        "{{TITLE}}": html.escape(title),
        "{{ABSTRACT}}": html.escape(abstract),
        "{{EXERCISE_BUTTON}}": exercise_button,
    }

    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    fragment = BeautifulSoup(rendered, "html.parser")
    article = fragment.select_one("article.course-card")

    if article is not None:
        return [article.extract()]

    # Veilige fallback wanneer de template geen geldige kaart oplevert.
    fallback = BeautifulSoup("", "html.parser")

    article = fallback.new_tag("article")
    article["class"] = ["course-card"]

    link = fallback.new_tag("a", href=url)
    link["class"] = ["course-card-link"]

    header = fallback.new_tag("div")
    header["class"] = ["course-card-header"]

    number_block = fallback.new_tag("div")
    number_block["class"] = ["course-card-number-block"]

    label = fallback.new_tag("span")
    label["class"] = ["course-card-label"]
    label.string = "Hoofdstuk"

    number_tag = fallback.new_tag("span")
    number_tag["class"] = ["course-card-number"]
    number_tag.string = number

    number_block.append(label)
    number_block.append(number_tag)

    title_tag = fallback.new_tag("h3")
    title_tag["class"] = ["course-card-title"]
    title_tag.string = title

    header.append(number_block)
    header.append(title_tag)

    abstract_tag = fallback.new_tag("p")
    abstract_tag["class"] = ["course-card-abstract"]
    abstract_tag.string = abstract or (
        "Open dit hoofdstuk om de leerstof, voorbeelden en oefeningen te bekijken."
    )

    footer = fallback.new_tag("div")
    footer["class"] = ["course-card-footer"]

    button = fallback.new_tag("span")
    button["class"] = ["course-card-button"]
    button.string = "Hoofdstuk openen →"

    footer.append(button)

    link.append(header)
    link.append(abstract_tag)
    link.append(footer)
    article.append(link)

    return [article]


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

        # --------------------------------------------------------
    # Theorie + oefeningen koppelen tot één hoofdstukkaart
    # --------------------------------------------------------

    chapter_groups: list[tuple[Tag, str, str | None]] = []

    activity_index = 0

    while activity_index < len(activity_links):
        link = activity_links[activity_index]

        href = str(link.get("href", "")).strip()

        activity = re.sub(
            r"(?:\.html)+$",
            "",
            href.rstrip("/"),
            flags=re.IGNORECASE,
        )

        # Een oefeningenactivity hoort bij het voorgaande
        # theoriehoofdstuk en krijgt dus geen eigen kaart.
        if Path(activity).name.casefold().startswith("oefeningen-"):
            activity_index += 1
            continue

        exercise_activity = None

        # Kijk of de volgende activity de oefeningen bij dit
        # theoriehoofdstuk zijn.
        if activity_index + 1 < len(activity_links):
            next_link = activity_links[activity_index + 1]

            next_href = str(
                next_link.get("href", "")
            ).strip()

            next_activity = re.sub(
                r"(?:\.html)+$",
                "",
                next_href.rstrip("/"),
                flags=re.IGNORECASE,
            )

            if Path(next_activity).name.casefold().startswith(
                "oefeningen-"
            ):
                exercise_activity = next_activity
                activity_index += 1

        chapter_groups.append(
            (
                link,
                activity,
                exercise_activity,
            )
        )

        activity_index += 1


    chapter_count = len(chapter_groups)

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


    # --------------------------------------------------------
    # Alleen theoriehoofdstukken krijgen een kaart
    # --------------------------------------------------------

    for chapter_index, (
        link,
        activity,
        exercise_activity,
    ) in enumerate(
        chapter_groups,
        start=1,
    ):

        chapter_title, abstract = read_chapter_metadata(
            module_dir,
            activity,
        )

        # Verwijder eventueel achtervoegsel met moduletitel.
        module_name_pattern = re.escape(
            module_dir.name.replace("-", " ").replace("_", " ")
        )

        chapter_title = re.sub(
            rf"\s*[–—-]\s*{module_name_pattern}\s*$",
            "",
            chapter_title,
            flags=re.IGNORECASE,
        )

        href_name = f"{activity}.html"

        exercise_url = (
            f"{exercise_activity}.html"
            if exercise_activity
            else None
        )

        chapter_number = str(chapter_index)

        for card_node in render_card(
            url=href_name,
            number=chapter_number,
            title=chapter_title,
            abstract=abstract,
            exercise_url=exercise_url,
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
#
# De footer wordt via BeautifulSoup rechtstreeks als laatste kind
# van <body> geplaatst. Daardoor kan hij niet per ongeluk binnen
# een hoofdstukkaart, grid of themablok terechtkomen.
#

XOURSE_HTML="$XOURSE_HTML" \
FOOTER_FILE="$FOOTER_FILE" \
MODULE_TITLE="$MODULE_TITLE" \
python3 - <<'PYFOOTER'
from __future__ import annotations

import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, Comment


html_file = Path(os.environ["XOURSE_HTML"])
footer_file = Path(os.environ["FOOTER_FILE"])
module_title = os.environ["MODULE_TITLE"]

document = html_file.read_text(encoding="utf-8")
footer_html = footer_file.read_text(encoding="utf-8")

replacements = {
    "{{MODULE_TITLE}}": module_title,
    "{{MODULE}}": module_title,
    "{{CHAPTER_TITLE}}": "",
    "{{CHAPTER_NUMBER}}": "",
    "{{CHAPTER_LOCAL_NUMBER}}": "",
    "{{THEME}}": "",
    "{{THEME_NUMBER}}": "",
    "{{ABSTRACT}}": "",
    "{{ASSET_PREFIX}}": "../../assets",
}

for placeholder, value in replacements.items():
    footer_html = footer_html.replace(placeholder, value)

soup = BeautifulSoup(document, "lxml")

if soup.body is None:
    raise RuntimeError("Geen <body> gevonden in het moduleoverzicht.")

# Verwijder een eventueel eerder geïnjecteerde footer.
start_comment = None
end_comment = None

for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
    normalized = re.sub(r"\s+", " ", str(comment)).strip()

    if normalized == "XIMERA-FOOTER-START":
        start_comment = comment

    elif normalized == "XIMERA-FOOTER-END":
        end_comment = comment

if start_comment is not None and end_comment is not None:
    current = start_comment

    while current is not None:
        next_node = current.next_sibling
        current.extract()

        if current is end_comment:
            break

        current = next_node

# Verwijder ook los achtergebleven footers en clear-elementen.
for old_footer in soup.select("footer.site-footer"):
    old_footer.decompose()

for old_clear in soup.select(".course-footer-clear"):
    old_clear.decompose()

footer_fragment = BeautifulSoup(footer_html, "html.parser")
footer = footer_fragment.select_one("footer.site-footer")

if footer is None:
    raise RuntimeError(
        "Footer.html bevat geen <footer class=\"site-footer\">."
    )

clear = soup.new_tag("div")
clear["class"] = ["course-footer-clear"]

# Expliciet als directe kinderen van body invoegen.
soup.body.append(clear)
soup.body.append(Comment(" XIMERA-FOOTER-START "))
soup.body.append(footer.extract())
soup.body.append(Comment(" XIMERA-FOOTER-END "))

# Extra zekerheid dat de footer altijd over de volle breedte staat.
style = soup.new_tag("style")
style["id"] = "FVD-FOOTER-LAYOUT-FIX"
style.string = """
.course-footer-clear {
    display: block;
    width: 100%;
    clear: both;
}

body > .site-footer {
    display: block;
    width: 100%;
    max-width: none;
    clear: both;
    box-sizing: border-box;
}
"""

old_style = soup.find("style", id="FVD-FOOTER-LAYOUT-FIX")

if old_style is not None:
    old_style.replace_with(style)
elif soup.head is not None:
    soup.head.append(style)

html_file.write_text(
    str(soup) + "\n",
    encoding="utf-8",
)
PYFOOTER

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