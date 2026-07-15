#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULES_DIR="modules"

shopt -s nullglob

MODULE_FILES=("$MODULES_DIR"/*/index.tex)

if [ ${#MODULE_FILES[@]} -eq 0 ]; then
    echo "Geen modules gevonden in $MODULES_DIR."
    exit 0
fi

echo
echo "========================================"
echo " Wiskundecursus bouwen"
echo "========================================"
echo

for course_file in "${MODULE_FILES[@]}"
do
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

    echo "3. Hoofdstukken opmaken"

    bash scripts/convert-ximera.sh "$module_dir"

    echo "4. PDF genereren"

    xmlatex bake \
        --force \
        --compile pdf \
        "$course_file"

    echo "Module $module_name is klaar."
done

echo
echo "========================================"
echo " Alle modules zijn verwerkt"
echo "========================================"