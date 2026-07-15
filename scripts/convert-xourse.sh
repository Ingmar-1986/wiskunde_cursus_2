#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULE_DIR="${1:-}"

if [ -z "$MODULE_DIR" ]; then
    echo "Gebruik: $0 modules/naam-van-module"
    exit 1
fi

XOURSE_HTML="$MODULE_DIR/index.html"

ASSETS_DIR="assets"
HTML_DIR="$ASSETS_DIR/html"
CSS_DIR="$ASSETS_DIR/css"
JS_DIR="$ASSETS_DIR/js"

HEADER_FILE="$HTML_DIR/Header.html"
INTRO_FILE="$HTML_DIR/ModuleIntro.html"
FOOTER_FILE="$HTML_DIR/Footer.html"

# Vanuit modules/modulenaam/index.html zijn twee niveaus nodig.
HEADER_FOOTER_CSS="../../assets/css/Header_Footer.css"
MODULE_CSS="../../assets/css/ModuleLayout.css"
THEME_SCRIPT="../../assets/js/theme-toggle.js"

for required_file in \
    "$XOURSE_HTML" \
    "$HEADER_FILE" \
    "$INTRO_FILE" \
    "$FOOTER_FILE" \
    "$CSS_DIR/Header_Footer.css" \
    "$CSS_DIR/ModuleLayout.css" \
    "$JS_DIR/theme-toggle.js"
do
    if [ ! -f "$required_file" ]; then
        echo "Fout: $required_file werd niet gevonden."
        exit 1
    fi
done

echo "Verwerk moduleoverzicht: $XOURSE_HTML"

# CSS toevoegen

if ! grep -q "$HEADER_FOOTER_CSS" "$XOURSE_HTML"; then
    sed -i \
    "s#</head>#  <link href='$HEADER_FOOTER_CSS' media='screen' rel='stylesheet' />\n</head>#" \
    "$XOURSE_HTML"
fi

if ! grep -q "$MODULE_CSS" "$XOURSE_HTML"; then
    sed -i \
    "s#</head>#  <link href='$MODULE_CSS' media='screen' rel='stylesheet' />\n</head>#" \
    "$XOURSE_HTML"
fi

# Header toevoegen

if ! grep -q "XIMERA-HEADER-START" "$XOURSE_HTML"; then
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
fi

# Module-intro toevoegen

if ! grep -q "XIMERA-INTRO-START" "$XOURSE_HTML"; then
    sed -i \
    '/<!-- XIMERA-HEADER-END -->/a\
<!-- XIMERA-INTRO-START -->\
<!-- INTRO-PLACEHOLDER -->\
<!-- XIMERA-INTRO-END -->' \
    "$XOURSE_HTML"

    sed -i \
    "/<!-- INTRO-PLACEHOLDER -->/r $INTRO_FILE" \
    "$XOURSE_HTML"

    sed -i \
    '/<!-- INTRO-PLACEHOLDER -->/d' \
    "$XOURSE_HTML"
fi

# Themahoofden omzetten

sed -E -i \
"s#<h1 class='card part' id='(part[0-9]+)'>([^<]*)</h1>#<div class=\"activity-card card-sectionheading card part\" id=\"\1\"><div class=\"card-block\"><h4 class=\"card-title\">\2</h4></div></div>#g" \
"$XOURSE_HTML"

# Paragraaf rond kaarten verwijderen

perl -0pi -e "
s{
    <p>\s*
    (
        (?:
            <a\s+class='activity\ card\ '\s+.*?</a>\s*
        )+
    )
    </p>
}{
    \$1
}gsx;
" "$XOURSE_HTML"

# Dubbel Ximera-abstract verwijderen

perl -0pi -e "
s{
    <div class='abstract'>
    .*?
    </div>
}{}gsx;
" "$XOURSE_HTML"

# Footer toevoegen

if ! grep -q "XIMERA-FOOTER-START" "$XOURSE_HTML"; then
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
fi

# JavaScript toevoegen

if ! grep -q "$THEME_SCRIPT" "$XOURSE_HTML"; then
    sed -i \
    "s#</body>#  <script src='$THEME_SCRIPT'></script>\n</body>#" \
    "$XOURSE_HTML"
fi

echo "Moduleoverzicht verwerkt: $XOURSE_HTML"