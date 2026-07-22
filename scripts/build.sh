#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# XIMERA-BUILD
#
# Bouwt:
#   1. HTML voor de volledige module
#   2. Sidebar en verrijkte hoofdstukpagina's
#   3. Eén volledige cursus-PDF
#   4. Eén afzonderlijke PDF per hoofdstuk
#   5. Een nette dist-map met alle PDF's
#
# Gebruik:
#   ./scripts/build.sh
#   ./scripts/build.sh modules/basiswiskunde
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODULE_DIR="${1:-modules/basiswiskunde}"
INDEX_TEX="$MODULE_DIR/index.tex"

MODULE_SLUG="$(basename "$MODULE_DIR")"
DIST_DIR="$PROJECT_ROOT/dist/$MODULE_SLUG"
CHAPTER_DIST_DIR="$DIST_DIR/hoofdstukken"
MANIFEST_FILE="$(mktemp)"

cleanup() {
    rm -f -- "$MANIFEST_FILE"
}
trap cleanup EXIT

section() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

fail() {
    echo
    echo "FOUT: $1" >&2
    exit 1
}

# ============================================================
# CONTROLES
# ============================================================

[[ -d "$MODULE_DIR" ]] ||
    fail "Modulemap niet gevonden: $MODULE_DIR"

[[ -f "$INDEX_TEX" ]] ||
    fail "index.tex niet gevonden: $INDEX_TEX"

[[ -x xmScripts/xmlatex ]] ||
    fail "xmScripts/xmlatex ontbreekt of is niet uitvoerbaar"

[[ -f scripts/generate-sidebar.sh ]] ||
    fail "scripts/generate-sidebar.sh ontbreekt"

[[ -f scripts/enhance-chapter.py ]] ||
    fail "scripts/enhance-chapter.py ontbreekt"

command -v python3 >/dev/null 2>&1 ||
    fail "python3 werd niet gevonden"

# ============================================================
# HOOFDSTUKKENMANIFEST MAKEN
#
# Uitvoer per regel:
# nummer<TAB>activity<TAB>titel<TAB>tex-bestand
# ============================================================

python3 - "$MODULE_DIR" "$INDEX_TEX" > "$MANIFEST_FILE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

module_dir = Path(sys.argv[1])
index_file = Path(sys.argv[2])

source = index_file.read_text(encoding="utf-8")

def remove_comments(text: str) -> str:
    cleaned = []
    for line in text.splitlines():
        result = []
        escaped = False
        for char in line:
            if char == "%" and not escaped:
                break
            result.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        cleaned.append("".join(result))
    return "\n".join(cleaned)

def clean_text(value: str) -> str:
    value = value.strip()
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\#": "#",
        r"\_": "_",
        "~": " ",
        "---": "—",
        "--": "–",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    previous = None
    while previous != value:
        previous = value
        value = re.sub(
            r"\\(?:textbf|textit|emph|mathrm|mathbf|mathit|textrm|textsf|texttt|mbox)\s*\{([^{}]*)\}",
            r"\1",
            value,
        )

    value = re.sub(r"\\[a-zA-Z@]+\*?", "", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value

def activity_base(activity: str) -> str:
    activity = activity.strip().replace("\\", "/")
    if activity.endswith(".tex"):
        activity = activity[:-4]
    if activity.endswith("/index"):
        activity = activity[:-6]
    return activity

def resolve_tex(activity: str) -> Path:
    raw = activity.strip()
    path = Path(raw)

    candidates = []
    if path.suffix == ".tex":
        candidates.append(module_dir / path)
    else:
        candidates.extend(
            [
                module_dir / f"{raw}.tex",
                module_dir / raw / f"{path.name}.tex",
                module_dir / raw / "index.tex",
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return candidates[0]

def extract_title(tex_file: Path, activity: str) -> str:
    fallback = Path(activity_base(activity)).name.replace("-", " ").replace("_", " ")
    fallback = fallback[:1].upper() + fallback[1:] if fallback else "Hoofdstuk"

    if not tex_file.is_file():
        return fallback

    text = remove_comments(tex_file.read_text(encoding="utf-8"))
    match = re.search(
        r"\\(?:title|fvdtitle|activitytitle|chaptertitle)\s*\{([^{}]*)\}",
        text,
    )
    return clean_text(match.group(1)) if match else fallback

source = remove_comments(source)

token_pattern = re.compile(
    r"\\part\s*\{(?P<part>[^{}]*)\}|"
    r"\\activity(?:\[[^]]*\])?\s*\{(?P<activity>[^{}]*)\}"
)

theme_number = 0
chapter_number = 0

for match in token_pattern.finditer(source):
    if match.group("part") is not None:
        theme_number += 1
        chapter_number = 0
        continue

    activity = match.group("activity")
    if activity is None:
        continue

    if theme_number == 0:
        theme_number = 1

    chapter_number += 1
    base = activity_base(activity)
    tex_file = resolve_tex(activity)
    title = extract_title(tex_file, activity)

    # Tabs en nieuwe regels zouden het manifest breken.
    title = title.replace("\t", " ").replace("\n", " ").strip()

    print(
        f"{theme_number}.{chapter_number}\t"
        f"{base}\t"
        f"{title}\t"
        f"{tex_file.as_posix()}"
    )
PY

[[ -s "$MANIFEST_FILE" ]] ||
    fail "Geen hoofdstukken gevonden in $INDEX_TEX"

mapfile -t MANIFEST_LINES < "$MANIFEST_FILE"

# ============================================================
# 1. HTML
# ============================================================

section "1. HTML genereren met Ximera"

xmScripts/xmlatex bake \
    --force \
    --compile html \
    "$INDEX_TEX"

# ============================================================
# 2. DOOR XIMERA AANGEMAAKTE GEWONE HTML VERWIJDEREN
#
# .online.html blijft behouden als schone bron.
# ============================================================

section "2. Gewone hoofdstuk-HTML verwijderen"

sudo -v

for line in "${MANIFEST_LINES[@]}"; do
    IFS=$'\t' read -r number activity title tex_file <<< "$line"
    output_file="$MODULE_DIR/$activity.html"

    if [[ -e "$output_file" ]]; then
        echo "Verwijderen: $output_file"
        sudo rm -f -- "$output_file"
    fi
done

# ============================================================
# 3. SIDEBAR
# ============================================================

section "3. Sidebar genereren"

bash scripts/generate-sidebar.sh "$MODULE_DIR"

# ============================================================
# 4. DEFINITIEVE HTML
# ============================================================

section "4. Hoofdstukken verrijken"

python3 scripts/enhance-chapter.py "$MODULE_DIR"

# ============================================================
# 5. VOLLEDIGE CURSUS-PDF
# ============================================================

section "5. Volledige cursus-PDF genereren"

xmScripts/xmlatex bake \
    --force \
    --compile pdf \
    "$INDEX_TEX"

FULL_PDF="$MODULE_DIR/index.pdf"

[[ -f "$FULL_PDF" ]] ||
    fail "De volledige cursus-PDF werd niet aangemaakt: $FULL_PDF"

# ============================================================
# 6. AFZONDERLIJKE HOOFDSTUK-PDF'S
# ============================================================

section "6. Afzonderlijke hoofdstuk-PDF's genereren"

chapter_failures=0

for line in "${MANIFEST_LINES[@]}"; do
    IFS=$'\t' read -r number activity title tex_file <<< "$line"

    echo
    echo "[$number] $title"
    echo "  bron: $tex_file"

    if [[ ! -f "$tex_file" ]]; then
        echo "  FOUT: TeX-bestand ontbreekt"
        chapter_failures=$((chapter_failures + 1))
        continue
    fi

    if ! xmScripts/xmlatex bake \
        --force \
        --compile pdf \
        "$tex_file"
    then
        echo "  FOUT: compilatie mislukt"
        chapter_failures=$((chapter_failures + 1))
        continue
    fi

    chapter_pdf="${tex_file%.tex}.pdf"

    if [[ ! -f "$chapter_pdf" ]]; then
        echo "  FOUT: PDF niet gevonden: $chapter_pdf"
        chapter_failures=$((chapter_failures + 1))
        continue
    fi

    echo "  OK: $chapter_pdf"
done

if (( chapter_failures > 0 )); then
    fail "$chapter_failures hoofdstuk-PDF('s) konden niet worden gebouwd"
fi

# ============================================================
# 7. DIST-MAP MAKEN
# ============================================================

section "7. PDF's verzamelen in dist"

rm -rf -- "$DIST_DIR"
mkdir -p "$CHAPTER_DIST_DIR"

cp -f -- "$FULL_PDF" "$DIST_DIR/${MODULE_SLUG}.pdf"

for line in "${MANIFEST_LINES[@]}"; do
    IFS=$'\t' read -r number activity title tex_file <<< "$line"

    chapter_pdf="${tex_file%.tex}.pdf"

    safe_title="$(
        printf '%s' "$title" |
        sed -E \
            -e 's/[\/\\:*?"<>|]+/-/g' \
            -e 's/[[:space:]]+/-/g' \
            -e 's/-+/-/g' \
            -e 's/^-|-$//g'
    )"

    [[ -n "$safe_title" ]] || safe_title="$(basename "$activity")"

    destination="$CHAPTER_DIST_DIR/${number}-${safe_title}.pdf"

    cp -f -- "$chapter_pdf" "$destination"
    echo "Geschreven: $destination"
done

# ============================================================
# 8. OVERZICHT
# ============================================================

section "Build voltooid"

echo "Website:"
echo "  $MODULE_DIR"
echo
echo "Volledige cursus:"
echo "  $DIST_DIR/${MODULE_SLUG}.pdf"
echo
echo "Afzonderlijke hoofdstukken:"
echo "  $CHAPTER_DIST_DIR"
echo
find "$CHAPTER_DIST_DIR" -maxdepth 1 -type f -name '*.pdf' \
    -printf '  - %f\n' |
    sort


    echo
echo "Sidebar genereren..."
bash scripts/generate-sidebar.sh modules/basiswiskunde

echo
echo "Hoofdstukken verrijken..."
python3 scripts/enhance-chapter.py modules/basiswiskunde