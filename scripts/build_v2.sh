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
    # 5. PDF — theorie + oefeningen
    #    telkens leerlingenversie + uitwerkingen
    # --------------------------------------------------------

    log_step "5/9 PDF-versies genereren"

    local pdf_dir
    local exercise_index_tex

    local theory_student_pdf
    local theory_solutions_pdf
    local exercise_student_pdf
    local exercise_solutions_pdf

    pdf_dir="$module_dir/pdf"
    mkdir -p "$pdf_dir"

    exercise_index_tex="$module_dir/index_oefeningen.tex"

    theory_student_pdf="$pdf_dir/${module_name}_leerlingen.pdf"
    theory_solutions_pdf="$pdf_dir/${module_name}_uitwerkingen.pdf"

    exercise_student_pdf="$pdf_dir/${module_name}_oefeningen_leerlingen.pdf"
    exercise_solutions_pdf="$pdf_dir/${module_name}_oefeningen_uitwerkingen.pdf"


    # ========================================================
    # HULPFUNCTIE: ÉÉN PDF-VERSIE BOUWEN
    # ========================================================

    build_pdf_variant() {
        local source_tex="$1"
        local destination_pdf="$2"
        local handout_mode="$3"
        local label="$4"

        local source_stem
        local build_tex
        local build_stem
        local temp_tex
        local built_pdf
        local candidate
        local stamp

        source_stem="$(basename "$source_tex" .tex)"

        build_tex="$source_tex"
        build_stem="$source_stem"
        temp_tex=""

        echo
        echo "  $label genereren"

        # ----------------------------------------------------
        # Leerlingenversie:
        # tijdelijke xourse maken met \handouttrue
        # ----------------------------------------------------

        if [[ "$handout_mode" == "true" ]]; then

            temp_tex="$module_dir/${source_stem}_leerlingen.tmp.tex"

            cp "$source_tex" "$temp_tex"

            python3 - "$temp_tex" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])

text = path.read_text(
    encoding="utf-8"
)

# Eventuele bestaande \handouttrue verwijderen.
text = re.sub(
    r'(?m)^[ \t]*\\handouttrue[ \t]*\n?',
    '',
    text,
)

pattern = (
    r'(\\documentclass'
    r'(?:\[[^\]]*\])?'
    r'\{xourse\})'
)

if not re.search(pattern, text):
    raise SystemExit(
        f"Fout: \\documentclass{{xourse}} "
        f"niet gevonden in {path}"
    )

text = re.sub(
    pattern,
    r'\1\n\n\\handouttrue',
    text,
    count=1,
)

path.write_text(
    text,
    encoding="utf-8",
)
PY

            build_tex="$temp_tex"
            build_stem="$(basename "$temp_tex" .tex)"

            echo "  └─ tijdelijke kopie met \\handouttrue"

        else

            echo "  └─ volledige versie met uitwerkingen"

        fi


        # ----------------------------------------------------
        # Tijdstip registreren
        # ----------------------------------------------------

        stamp="$(mktemp)"
        touch "$stamp"


        # ----------------------------------------------------
        # PDF bouwen
        # ----------------------------------------------------

        xmlatex bake \
            --force \
            --compile pdf \
            "$build_tex"


        # ----------------------------------------------------
        # Nieuwe PDF terugvinden
        # ----------------------------------------------------

        built_pdf=""

        for candidate in \
            "$module_dir/${build_stem}.pdf" \
            "ximera-downloads/without-answers/$module_dir/${build_stem}.pdf" \
            "ximera-downloads/with-answers/$module_dir/${build_stem}.pdf"
        do
            if [[ -f "$candidate" && "$candidate" -nt "$stamp" ]]; then
                built_pdf="$candidate"
                break
            fi
        done

        rm -f "$stamp"


        # ----------------------------------------------------
        # Controle
        # ----------------------------------------------------

        if [[ -z "$built_pdf" ]]; then

            if [[ -n "$temp_tex" ]]; then
                rm -f "$temp_tex"
            fi

            fail "$label werd niet gevonden na de PDF-build."
        fi


        # ----------------------------------------------------
        # Definitieve PDF bewaren
        # ----------------------------------------------------

        cp "$built_pdf" "$destination_pdf"


        # Alleen onze tijdelijke bron verwijderen.
        if [[ -n "$temp_tex" ]]; then
            rm -f "$temp_tex"
        fi

        echo "  ✓ $destination_pdf"
    }


    # ========================================================
    # 5A. THEORIE — LEERLINGEN
    # ========================================================

    build_pdf_variant \
        "$index_tex" \
        "$theory_student_pdf" \
        "true" \
        "Theorie — leerlingenversie"


    # ========================================================
    # 5B. THEORIE — UITWERKINGEN
    # ========================================================

    build_pdf_variant \
        "$index_tex" \
        "$theory_solutions_pdf" \
        "false" \
        "Theorie — uitwerkingen"


    # ========================================================
    # 5C + 5D. OEFENINGEN
    # ========================================================

    if [[ -f "$exercise_index_tex" ]]; then

        build_pdf_variant \
            "$exercise_index_tex" \
            "$exercise_student_pdf" \
            "true" \
            "Oefeningen — leerlingenversie"

        build_pdf_variant \
            "$exercise_index_tex" \
            "$exercise_solutions_pdf" \
            "false" \
            "Oefeningen — uitwerkingen"

    else

        echo
        echo "  Geen index_oefeningen.tex gevonden."
        echo "  Oefeningen-PDF's worden overgeslagen."

    fi


    # ========================================================
    # OVERZICHT
    # ========================================================

    echo
    echo "  PDF-build klaar:"
    echo
    echo "    Theorie leerlingen:"
    echo "      $theory_student_pdf"
    echo
    echo "    Theorie uitwerkingen:"
    echo "      $theory_solutions_pdf"

    if [[ -f "$exercise_index_tex" ]]; then
        echo
        echo "    Oefeningen leerlingen:"
        echo "      $exercise_student_pdf"
        echo
        echo "    Oefeningen uitwerkingen:"
        echo "      $exercise_solutions_pdf"
    fi

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