#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# INSTELLINGEN
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODULE="${1:-modules/basiswiskunde}"
MODULE_PATH="$PROJECT_ROOT/$MODULE"
INDEX_FILE="$MODULE_PATH/index.tex"

ENHANCE_SCRIPT="$PROJECT_ROOT/scripts/enhance-chapters.py"
SIDEBAR_SCRIPT="$PROJECT_ROOT/scripts/generate-sidebar.sh"

# ============================================================
# CONTROLES
# ============================================================

echo
echo "Ximera webbuild"
echo "────────────────────────────────────────"
echo "Project: $PROJECT_ROOT"
echo "Module:  $MODULE_PATH"
echo

if [[ ! -d "$MODULE_PATH" ]]; then
    echo "Fout: modulemap bestaat niet:"
    echo "  $MODULE_PATH"
    exit 1
fi

if [[ ! -f "$INDEX_FILE" ]]; then
    echo "Fout: index.tex ontbreekt:"
    echo "  $INDEX_FILE"
    exit 1
fi

if [[ ! -f "$ENHANCE_SCRIPT" ]]; then
    echo "Fout: enhance-script ontbreekt:"
    echo "  $ENHANCE_SCRIPT"
    exit 1
fi

if [[ ! -f "$SIDEBAR_SCRIPT" ]]; then
    echo "Fout: sidebar-script ontbreekt:"
    echo "  $SIDEBAR_SCRIPT"
    exit 1
fi

# ============================================================
# STAP 1 — XIMERA HTML
# ============================================================

echo "[1/3] Ximera-HTML genereren"
echo

cd "$PROJECT_ROOT"

find "$MODULE_PATH" \
    -maxdepth 1 \
    -type f \
    -name "*.html" \
    ! -name "*.online.html" \
    ! -name "CourseSidebar.generated.html" \
    -delete

xmlatex bake "$INDEX_FILE"

echo
echo "Ximera-HTML klaar."
echo

# ============================================================
# STAP 2 — SIDEBAR
# ============================================================

echo "[2/3] Cursuszijbalk genereren"
echo

bash "$SIDEBAR_SCRIPT" "$MODULE"

echo
echo "Sidebar klaar."
echo

# ============================================================
# STAP 3 — HOOFDSTUKKEN VERRIJKEN
# ============================================================

echo "[3/3] Hoofdstukken verwerken"
echo

python3 "$ENHANCE_SCRIPT" "$MODULE"

echo
echo "────────────────────────────────────────"
echo "Webbuild succesvol voltooid."
echo