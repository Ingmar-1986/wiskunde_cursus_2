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

    # Alleen HTML genereren.
    # De twee PDF-versies worden afzonderlijk in stap 5 gebouwd.
    xmlatex bake \
        --force \
        --compile html \
        "$index_tex"


       # --------------------------------------------------------
    # 5. PDF — leerlingenversie + uitwerkingenversie
    # --------------------------------------------------------

    log_step "5/9 PDF-versies van de volledige module genereren"

    local pdf_dir
    local student_tex
    local student_stem
    local student_pdf
    local solutions_pdf
    local built_pdf
    local stamp

    pdf_dir="$module_dir/pdf"
    mkdir -p "$pdf_dir"

    student_tex="$module_dir/index_leerlingen.tmp.tex"
    student_stem="index_leerlingen.tmp"

    student_pdf="$pdf_dir/${module_name}_leerlingen.pdf"
    solutions_pdf="$pdf_dir/${module_name}_uitwerkingen.pdf"


    # ========================================================
    # 5A. LEERLINGENVERSIE
    # ========================================================

    echo
    echo "  Leerlingenversie genereren"
    echo "  └─ tijdelijke kopie met \\handouttrue"

    # Originele index kopiëren.
    cp "$index_tex" "$student_tex"

    # \handouttrue invoegen na \documentclass{xourse}
    python3 - "$student_tex" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

# Zorg dat er niet toevallig al een handouttrue staat.
text = re.sub(
    r'(?m)^[ \t]*\\handouttrue[ \t]*\n?',
    '',
    text
)

pattern = r'(\\documentclass(?:\[[^\]]*\])?\{xourse\})'

if not re.search(pattern, text):
    raise SystemExit(
        f"Fout: \\documentclass{{xourse}} niet gevonden in {path}"
    )

text = re.sub(
    pattern,
    r'\1\n\n\\handouttrue',
    text,
    count=1
)

path.write_text(text, encoding="utf-8")
PY

    # Tijdstip registreren zodat we alleen een NIEUWE PDF accepteren.
    stamp="$(mktemp)"
    touch "$stamp"

    xmlatex bake \
        --force \
        --compile pdf \
        "$student_tex"

    built_pdf=""

    # Ximera kan de PDF lokaal laten staan of naar zijn downloadmap verplaatsen.
    for candidate in \
        "$module_dir/${student_stem}.pdf" \
        "ximera-downloads/without-answers/$module_dir/${student_stem}.pdf" \
        "ximera-downloads/with-answers/$module_dir/${student_stem}.pdf"
    do
        if [[ -f "$candidate" && "$candidate" -nt "$stamp" ]]; then
            built_pdf="$candidate"
            break
        fi
    done

    rm -f "$stamp"

    if [[ -z "$built_pdf" ]]; then
        rm -f "$student_tex"
        fail "De leerlingen-PDF werd niet gevonden na de build."
    fi

    cp "$built_pdf" "$student_pdf"

    # Alleen ons eigen tijdelijke .tex-bestand verwijderen.
    rm -f "$student_tex"

    echo "  ✓ Leerlingen-PDF:"
    echo "    $student_pdf"


    # ========================================================
    # 5B. UITWERKINGENVERSIE
    # ========================================================

    echo
    echo "  Uitwerkingenversie genereren"
    echo "  └─ originele index.tex zonder \\handouttrue"

    stamp="$(mktemp)"
    touch "$stamp"

    xmlatex bake \
        --force \
        --compile pdf \
        "$index_tex"

    built_pdf=""

    for candidate in \
        "$module_dir/index.pdf" \
        "ximera-downloads/with-answers/$module_dir/index.pdf" \
        "ximera-downloads/without-answers/$module_dir/index.pdf"
    do
        if [[ -f "$candidate" && "$candidate" -nt "$stamp" ]]; then
            built_pdf="$candidate"
            break
        fi
    done

    rm -f "$stamp"

    [[ -n "$built_pdf" ]] \
        || fail "De uitwerkingen-PDF werd niet gevonden na de build."

    cp "$built_pdf" "$solutions_pdf"

    echo "  ✓ Uitwerkingen-PDF:"
    echo "    $solutions_pdf"

    echo
    echo "  Beide PDF-versies zijn klaar:"
    echo "    Leerlingen:   $student_pdf"
    echo "    Uitwerkingen: $solutions_pdf"

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