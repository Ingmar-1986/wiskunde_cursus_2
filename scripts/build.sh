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

    echo "3. Sidebar genereren"

    bash scripts/generate-sidebar.sh "$module_dir"

    echo "4. Hoofdstukken opmaken"

    bash scripts/convert-ximera.sh "$module_dir"

    echo "5. PDF genereren"

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
    fi
done