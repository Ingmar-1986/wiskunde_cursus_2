#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULES_ROOT="modules"
REQUESTED_MODULE="${1:-}"

# ============================================================
# HULPFUNCTIES
# ============================================================

log_section() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

log_step() {
    echo
    echo "$1"
}

fail() {
    echo
    echo "Fout: $1" >&2
    exit 1
}

module_has_index() {
    [[ -f "$1/index.tex" ]]
}

run_script() {
    local script="$1"
    shift

    [[ -f "$script" ]] || fail "$script werd niet gevonden."

    case "$script" in
        *.py)
            python3 "$script" "$@"
            ;;
        *.sh)
            bash "$script" "$@"
            ;;
        *)
            if [[ -x "$script" ]]; then
                "$script" "$@"
            else
                fail "Ik weet niet hoe '$script' uitgevoerd moet worden."
            fi
            ;;
    esac
}

run_optional_script() {
    local script="$1"
    shift

    if [[ ! -f "$script" ]]; then
        echo "Overgeslagen: $script bestaat niet."
        return 0
    fi

    run_script "$script" "$@"
}

check_python_script() {
    local script="$1"

    [[ -f "$script" ]] || fail "$script werd niet gevonden."

    python3 -m py_compile "$script"
}

first_existing_file() {
    local candidate

    for candidate in "$@"; do
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

# ============================================================
# ÉÉN MODULE BOUWEN
# ============================================================

build_module() {
    local module_dir="$1"
    local module_name
    local index_tex
    local generated_module_page
    local chapter_hero_template=""
    local module_banner_template=""

    module_name="$(basename "$module_dir")"
    index_tex="$module_dir/index.tex"
    generated_module_page="$module_dir/module-opening.generated.tex"

    log_section "Module bouwen: $module_name"

    if ! module_has_index "$module_dir"; then
        echo "Overgeslagen: $module_dir bevat geen index.tex."
        return 0
    fi

    # Zowel hoofdletters als kleine letters ondersteunen.
    chapter_hero_template="$(
        first_existing_file \
            "assets/html/ChapterHero.html" \
            "assets/html/chapter-hero.html" \
        || true
    )"

    module_banner_template="$(
        first_existing_file \
            "assets/html/module-banner.html" \
            "assets/html/ModuleBanner.html" \
        || true
    )"

    # --------------------------------------------------------
    # 1. PYTHONSCRIPTS CONTROLEREN
    # --------------------------------------------------------

    log_step "1/9 Generators en scripts controleren"

    check_python_script "scripts/generate-theme-overviews.py"
    check_python_script "scripts/generate-module-overview.py"

    if [[ -f "scripts/inject-chapter-heroes.py" ]]; then
        check_python_script "scripts/inject-chapter-heroes.py"
    fi

    if [[ -f "scripts/enhance-chapter.py" ]]; then
        check_python_script "scripts/enhance-chapter.py"
    fi

    # --------------------------------------------------------
    # 2. THEMAOVERZICHTEN
    # --------------------------------------------------------

    log_step "2/9 Hoofdstukoverzichten per thema genereren"

    python3 "scripts/generate-theme-overviews.py" \
        "$index_tex" \
        --no-backup

    # --------------------------------------------------------
    # 3. MODULEOPENING VOOR PDF
    # --------------------------------------------------------

    log_step "3/9 Moduleopening met themaoverzicht genereren"

    python3 "scripts/generate-module-overview.py" \
        "$index_tex"

    [[ -f "$generated_module_page" ]] \
        || fail "De moduleopening werd niet aangemaakt: $generated_module_page"

    # --------------------------------------------------------
    # 4. XIMERA EN HTML
    # --------------------------------------------------------

    log_step "4/9 Ximera- en HTML-bestanden genereren"

    xmlatex bake \
        --force \
        "$index_tex"

    # --------------------------------------------------------
    # 5. PDF
    # --------------------------------------------------------

    log_step "5/9 PDF van de volledige module genereren"

    xmlatex bake \
        --force \
        --compile pdf \
        "$index_tex"

    # --------------------------------------------------------
    # 6. SIDEBAR
    # Moet vóór enhance-chapter.py gebeuren.
    # --------------------------------------------------------

    log_step "6/9 Sidebar genereren"

    run_optional_script \
        "scripts/generate-sidebar.sh" \
        "$module_dir"

    # --------------------------------------------------------
    # 7. HOOFDSTUKPAGINA'S
    # --------------------------------------------------------

    log_step "7/9 Hoofdstukpagina's verbeteren"

    if [[ -f "scripts/enhance-chapter.py" ]]; then
        python3 "scripts/enhance-chapter.py" \
            "$module_dir"

    elif [[ -f "scripts/enhance-chapter.sh" ]]; then
        bash "scripts/enhance-chapter.sh" \
            "$module_dir"

    else
        echo "Overgeslagen: geen enhance-chapter-script gevonden."
    fi

    # --------------------------------------------------------
    # 8. MODULEOVERZICHT WEBSITE
    # --------------------------------------------------------

    log_step "8/9 Moduleoverzicht voor de website verbeteren"

    run_optional_script \
        "scripts/convert-xourse.sh" \
        "$module_dir"

    # --------------------------------------------------------
    # 9. HERO'S EN MODULEBANNER INJECTEREN
    # Dit gebeurt als laatste, zodat convert-xourse.sh de banner
    # niet opnieuw kan overschrijven.
    # --------------------------------------------------------

    log_step "9/9 Hoofdstukhero's en modulebanner injecteren"

    if [[ ! -f "scripts/inject-chapter-heroes.py" ]]; then
        echo "Overgeslagen: scripts/inject-chapter-heroes.py ontbreekt."

    elif [[ -z "$chapter_hero_template" ]]; then
        echo "Overgeslagen: ChapterHero.html of chapter-hero.html ontbreekt."

    elif [[ -z "$module_banner_template" ]]; then
        echo "Modulebanner overgeslagen: module-banner.html ontbreekt."

        python3 "scripts/inject-chapter-heroes.py" \
            "$module_dir" \
            "$index_tex" \
            "$chapter_hero_template"

    else
        python3 "scripts/inject-chapter-heroes.py" \
            "$module_dir" \
            "$index_tex" \
            "$chapter_hero_template" \
            "$module_banner_template"
    fi

    echo
    echo "Klaar: $module_name"
    echo "Modulebron:       $index_tex"
    echo "Moduleopening:    $generated_module_page"
    echo "Hoofdstukhero:    ${chapter_hero_template:-niet gevonden}"
    echo "Modulebanner:     ${module_banner_template:-niet gevonden}"
}

# ============================================================
# ALGEMENE CONTROLES
# ============================================================

command -v xmlatex >/dev/null 2>&1 \
    || fail "xmlatex werd niet gevonden. Activeer eerst je Ximera-omgeving."

command -v python3 >/dev/null 2>&1 \
    || fail "python3 werd niet gevonden."

[[ -d "$MODULES_ROOT" ]] \
    || fail "De map '$MODULES_ROOT' werd niet gevonden."

# ============================================================
# ÉÉN MODULE OF ALLE MODULES
# ============================================================

if [[ -n "$REQUESTED_MODULE" ]]; then
    if [[ "$REQUESTED_MODULE" == modules/* ]]; then
        module_dir="${REQUESTED_MODULE%/}"
    else
        module_dir="$MODULES_ROOT/${REQUESTED_MODULE%/}"
    fi

    [[ -d "$module_dir" ]] \
        || fail "De modulemap '$module_dir' bestaat niet."

    build_module "$module_dir"
else
    module_count=0

    for module_dir in "$MODULES_ROOT"/*; do
        [[ -d "$module_dir" ]] || continue
        module_has_index "$module_dir" || continue

        build_module "$module_dir"
        module_count=$((module_count + 1))
    done

    if [[ "$module_count" -eq 0 ]]; then
        fail "Geen modulemappen met een index.tex gevonden."
    fi

    log_section "Alle modules zijn gebouwd"
    echo "Aantal verwerkte modules: $module_count"
fi