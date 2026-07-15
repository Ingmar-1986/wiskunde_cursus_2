#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULE_DIR="${1:-}"

if [ -z "$MODULE_DIR" ]; then
    echo "Gebruik: $0 modules/naam-van-module"
    exit 1
fi

ASSETS_DIR="assets"
HTML_DIR="$ASSETS_DIR/html"
CSS_DIR="$ASSETS_DIR/css"
JS_DIR="$ASSETS_DIR/js"

HEADER_FILE="$HTML_DIR/Header.html"
SIDEBAR_FILE="$MODULE_DIR/CourseSidebar.generated.html"
FOOTER_FILE="$HTML_DIR/Footer.html"

HEADER_FOOTER_CSS="../../assets/css/Header_Footer.css"
CHAPTER_CSS="../../assets/css/ChapterLayout.css"
CHAPTER_SCRIPT="../../assets/js/chapter-layout.js"

shopt -s nullglob

ALL_HTML_FILES=("$MODULE_DIR"/*.html)
CHAPTER_FILES=()

for html_file in "${ALL_HTML_FILES[@]}"
do
    if [ "$(basename "$html_file")" != "index.html" ]; then
        CHAPTER_FILES+=("$html_file")
    fi
done

if [ ${#CHAPTER_FILES[@]} -eq 0 ]; then
    echo "Geen hoofdstukpagina's gevonden in $MODULE_DIR."
    exit 0
fi

for required_file in \
    "$HEADER_FILE" \
    "$SIDEBAR_FILE" \
    "$FOOTER_FILE" \
    "$CSS_DIR/Header_Footer.css" \
    "$CSS_DIR/ChapterLayout.css" \
    "$JS_DIR/chapter-layout.js"
do
    if [ ! -f "$required_file" ]; then
        echo "Fout: $required_file werd niet gevonden."
        exit 1
    fi
done

for f in "${CHAPTER_FILES[@]}"
do
    echo "Verwerk hoofdstuk: $f"

    # CSS toevoegen

    if ! grep -q "$HEADER_FOOTER_CSS" "$f"; then
        sed -i \
        "s#</head>#  <link href='$HEADER_FOOTER_CSS' media='screen' rel='stylesheet' />\n</head>#" \
        "$f"
    fi

    if ! grep -q "$CHAPTER_CSS" "$f"; then
        sed -i \
        "s#</head>#  <link href='$CHAPTER_CSS' media='screen' rel='stylesheet' />\n</head>#" \
        "$f"
    fi

    # Header toevoegen

    if ! grep -q "XIMERA-HEADER-START" "$f"; then
        sed -i \
        's#<body[^>]*>#&\
<!-- XIMERA-HEADER-START -->\
<!-- HEADER-PLACEHOLDER -->\
<!-- XIMERA-HEADER-END -->#' \
        "$f"

        sed -i \
        "/<!-- HEADER-PLACEHOLDER -->/r $HEADER_FILE" \
        "$f"

        sed -i \
        '/<!-- HEADER-PLACEHOLDER -->/d' \
        "$f"
    fi

    # Hoofdstuklayout openen

    if ! grep -q "XIMERA-CHAPTER-LAYOUT-START" "$f"; then
        sed -i \
        '/<!-- XIMERA-HEADER-END -->/a\
<!-- XIMERA-CHAPTER-LAYOUT-START -->\
<button class="course-menu-button" id="courseMenuButton" type="button">☰ Toon cursusinhoud</button>\
<div class="course-sidebar-overlay" id="courseSidebarOverlay"></div>\
<main class="chapter-layout">\
<!-- SIDEBAR-PLACEHOLDER -->\
<article class="chapter-content">\
<div class="chapter-body">' \
        "$f"
    fi

    # Sidebar invoegen

    if grep -q "<!-- SIDEBAR-PLACEHOLDER -->" "$f"; then
        sed -i \
        "/<!-- SIDEBAR-PLACEHOLDER -->/r $SIDEBAR_FILE" \
        "$f"

        sed -i \
        '/<!-- SIDEBAR-PLACEHOLDER -->/d' \
        "$f"
    fi

    # Hoofdstuklayout sluiten

    if ! grep -q "XIMERA-CHAPTER-LAYOUT-END" "$f"; then
        sed -i \
        '/<\/body>/i\
</div>\
</article>\
</main>\
<!-- XIMERA-CHAPTER-LAYOUT-END -->' \
        "$f"
    fi

    # Footer toevoegen

    if ! grep -q "XIMERA-FOOTER-START" "$f"; then
        sed -i \
        '/<\/body>/i\
<div class="course-footer-clear"></div>\
<!-- XIMERA-FOOTER-START -->\
<!-- FOOTER-PLACEHOLDER -->\
<!-- XIMERA-FOOTER-END -->' \
        "$f"

        sed -i \
        "/<!-- FOOTER-PLACEHOLDER -->/r $FOOTER_FILE" \
        "$f"

        sed -i \
        '/<!-- FOOTER-PLACEHOLDER -->/d' \
        "$f"
    fi

    # JavaScript toevoegen

    if ! grep -q "$CHAPTER_SCRIPT" "$f"; then
        sed -i \
        "s#</body>#  <script src='$CHAPTER_SCRIPT'></script>\n</body>#" \
        "$f"
    fi

    echo "Klaar: $f"
done