#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

shopt -s nullglob

MODULE_FILES=(modules/*/index.tex)

HERO_TEMPLATE="assets/html/chapter-hero.html"
HERO_SCRIPT="scripts/inject-chapter-heroes.py"

if [ ${#MODULE_FILES[@]} -eq 0 ]; then
    echo "Geen modules gevonden in modules/*/index.tex"
    exit 1
fi

if [ ! -f "$HERO_TEMPLATE" ]; then
    echo "Fout: hero-template niet gevonden:"
    echo "  $HERO_TEMPLATE"
    exit 1
fi

if [ ! -f "$HERO_SCRIPT" ]; then
    echo "Fout: automatisch hero-script niet gevonden:"
    echo "  $HERO_SCRIPT"
    exit 1
fi

echo
echo "========================================"
echo " Wiskundecursus bouwen"
echo "========================================"

for course_file in "${MODULE_FILES[@]}"; do
    module_dir="$(dirname "$course_file")"
    module_name="$(basename "$module_dir")"

    echo
    echo "----------------------------------------"
    echo "Module: $module_name"
    echo "----------------------------------------"

    echo "1. HTML genereren"

    xmlatex bake \
        --force \
        --compile html \
        "$course_file"

    echo "2. Moduleoverzicht opmaken"

    bash scripts/convert-xourse.sh "$module_dir"

    echo "3. Sidebar genereren"

    bash scripts/generate-sidebar.sh "$module_dir"

    echo "4. Hoofdstukken opmaken"

    bash scripts/convert-ximera.sh "$module_dir"

echo "5. Hoofdstukhero's invoegen"

hero_count=0

while IFS= read -r -d '' html_file; do
    if grep -q 'name="course-chapter-number"' "$html_file"; then
        echo "   Hero invoegen in: $html_file"

        python3 scripts/inject-chapter-hero.py \
            "$html_file" \
            "$HERO_TEMPLATE" \
            "$html_file"

        ((hero_count += 1))
    else
        echo "   Overslaan zonder metadata: $html_file"
    fi
done < <(
    find "$module_dir" \
        -maxdepth 1 \
        -type f \
        -name "*.html" \
        ! -name "index.html" \
        ! -name "*.online.html" \
        -print0
)

if [ "$hero_count" -eq 0 ]; then
    echo "   Waarschuwing: geen hoofdstukken met hero-metadata gevonden."
else
    echo "   $hero_count hoofdstukhero('s) ingevoegd."
fi

    echo "6. PDF genereren"

    xmlatex bake \
        --force \
        --compile pdf \
        "$course_file"

    mkdir -p pdf

    if [ -f "$module_dir/index.pdf" ]; then
        cp \
            "$module_dir/index.pdf" \
            "pdf/${module_name}.pdf"

        echo "PDF geplaatst in pdf/${module_name}.pdf"
    else
        echo "Waarschuwing: $module_dir/index.pdf werd niet gevonden."
    fi

    echo "Module $module_name is klaar."
done

echo
echo "========================================"
echo " Build voltooid"
echo "========================================"