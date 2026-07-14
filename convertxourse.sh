#!/usr/bin/env bash

set -e

# ============================================================
# INSTELLINGEN
# ============================================================

COURSE_DIR="testmodule"

HEADER_FILE="Header.html"
INTRO_FILE="ModuleIntro.html"
FOOTER_FILE="Footer.html"

COURSE_CSS="../test.css"
HEADER_FOOTER_CSS="../Header_Footer.css"

# Zorgt ervoor dat een lege map geen fout veroorzaakt.
shopt -s nullglob

HTML_FILES=("$COURSE_DIR"/*.html)

if [ ${#HTML_FILES[@]} -eq 0 ]; then
    echo "Geen HTML-bestanden gevonden in: $COURSE_DIR"
    exit 0
fi

# ============================================================
# BESTANDEN CONTROLEREN
# ============================================================

for required_file in "$HEADER_FILE" "$INTRO_FILE" "$FOOTER_FILE"
do
    if [ ! -f "$required_file" ]; then
        echo "Fout: $required_file werd niet gevonden."
        exit 1
    fi
done

# ============================================================
# HTML-BESTANDEN VERWERKEN
# ============================================================

for f in "${HTML_FILES[@]}"
do
    echo "Verwerk: $f"

    # --------------------------------------------------------
    # 1. Eigen CSS-bestanden toevoegen
    # --------------------------------------------------------

    if ! grep -q "$COURSE_CSS" "$f"; then
        sed -i \
        "s#</head>#  <link href='$COURSE_CSS' media='screen' rel='stylesheet' />\n  <link href='$HEADER_FOOTER_CSS' media='screen' rel='stylesheet' />\n</head>#" \
        "$f"
    fi

    # --------------------------------------------------------
    # 2. Header toevoegen
    # --------------------------------------------------------

    if ! grep -q "XIMERA-HEADER-START" "$f"; then
        sed -i \
        's#<body[^>]*>#&\
<!-- XIMERA-HEADER-START -->\
<!-- HEADER-PLACEHOLDER -->\
<!-- XIMERA-HEADER-END -->#' \
        "$f"

        sed -i \
        '/<!-- HEADER-PLACEHOLDER -->/r Header.html' \
        "$f"

        sed -i \
        '/<!-- HEADER-PLACEHOLDER -->/d' \
        "$f"
    fi

    # --------------------------------------------------------
    # 3. Module-intro toevoegen
    # De intro wordt direct na de header geplaatst.
    # --------------------------------------------------------

    if ! grep -q "XIMERA-INTRO-START" "$f"; then
        sed -i \
        '/<!-- XIMERA-HEADER-END -->/a\
<!-- XIMERA-INTRO-START -->\
<!-- INTRO-PLACEHOLDER -->\
<!-- XIMERA-INTRO-END -->' \
        "$f"

        sed -i \
        '/<!-- INTRO-PLACEHOLDER -->/r ModuleIntro.html' \
        "$f"

        sed -i \
        '/<!-- INTRO-PLACEHOLDER -->/d' \
        "$f"
    fi

    # --------------------------------------------------------
    # 4. Footer toevoegen
    # --------------------------------------------------------

    if ! grep -q "XIMERA-FOOTER-START" "$f"; then
        sed -i \
        '/<\/body>/i\
<!-- XIMERA-FOOTER-START -->\
<!-- FOOTER-PLACEHOLDER -->\
<!-- XIMERA-FOOTER-END -->' \
        "$f"

        sed -i \
        '/<!-- FOOTER-PLACEHOLDER -->/r Footer.html' \
        "$f"

        sed -i \
        '/<!-- FOOTER-PLACEHOLDER -->/d' \
        "$f"
    fi

    # --------------------------------------------------------
    # 5. Ximera-parts omzetten naar sectiekaarten
    #
    # Voorbeeld:
    #
    # <h1 class='card part' id='part1'>Eerste thema</h1>
    #
    # wordt:
    #
    # <div class="activity-card card-sectionheading card part"
    #      id="part1">
    #     <div class="card-block">
    #         <h4 class="card-title">Eerste thema</h4>
    #     </div>
    # </div>
    # --------------------------------------------------------

    sed -E -i \
    "s#<h1 class='card part' id='part([0-9]+)'>([^<]*)</h1>#<div class=\"activity-card card-sectionheading card part\" id=\"part\1\"><div class=\"card-block\"><h4 class=\"card-title\">\2</h4></div></div>#g" \
    "$f"

    # --------------------------------------------------------
    # 6. Lege paragrafen verwijderen
    #
    # Gewone paragrafen blijven behouden.
    # --------------------------------------------------------

    sed -E -i \
    's#<p>[[:space:]]*</p>##g' \
    "$f"

    echo "Klaar: $f"
done

echo
echo "Alle Ximera-HTML-bestanden zijn verwerkt."

