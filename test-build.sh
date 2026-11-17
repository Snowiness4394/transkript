#!/usr/bin/env bash
# test-build.sh — Verify that all dependencies and imports are ready for PyInstaller
# Run this before building to catch issues early

set -e
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} — $1"; }
fail() { echo -e "${RED}FAIL${NC} — $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}WARN${NC} — $1"; }

ERRORS=0

echo "=== transkript — PyInstaller Readiness Check ==="
echo ""

# 1. Check Python version
echo "--- Python ---"
PY_VERSION=$(uv run python --version 2>&1)
if uv run python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    pass "$PY_VERSION"
else
    fail "$PY_VERSION (need 3.11+)"
fi

# 2. Check uv
echo ""
echo "--- uv ---"
if command -v uv &> /dev/null; then
    pass "uv $(uv --version 2>&1 | head -1)"
else
    fail "uv not found — install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# 3. Install dependencies
echo ""
echo "--- Dependencies ---"
if uv sync --group dev >/dev/null 2>&1; then
    pass "Dependencies installed"
else
    fail "Dependency installation failed"
fi

# 4. Check PyInstaller
echo ""
echo "--- PyInstaller ---"
PYINSTALLER_VERSION=$(uv run pyinstaller --version 2>&1)
if [[ -n "$PYINSTALLER_VERSION" ]]; then
    pass "PyInstaller $PYINSTALLER_VERSION"
else
    fail "PyInstaller not found"
fi

# 5. Test all imports
echo ""
echo "--- Import checks ---"
IMPORTS=(
    "transkript"
    "transkript.app"
    "transkript.audio"
    "transkript.transcriber"
    "textual"
    "textual.app"
    "textual.widgets"
    "textual.containers"
    "sounddevice"
    "faster_whisper"
    "numpy"
)

for mod in "${IMPORTS[@]}"; do
    if uv run python -c "import $mod" 2>/dev/null; then
        pass "import $mod"
    else
        fail "import $mod"
    fi
done

# 6. Test app instantiation
echo ""
echo "--- App instantiation ---"
if uv run python -c "from transkript.app import TranskriptApp; app = TranskriptApp(); print(f'Title: {app.TITLE}')" 2>/dev/null; then
    pass "TranskriptApp created"
else
    fail "Could not create TranskriptApp"
fi

# 7. Check spec file exists
echo ""
echo "--- Build files ---"
if [[ -f "transkript.spec" ]]; then
    pass "transkript.spec exists"
else
    fail "transkript.spec missing"
fi

if [[ -f "build.sh" ]] || [[ -f "build.bat" ]]; then
    pass "Build scripts exist"
else
    fail "Build scripts missing"
fi

# 8. Check CSS file exists
echo ""
echo "--- Assets ---"
if [[ -f "src/transkript/styles/app.tcss" ]]; then
    pass "styles/app.tcss exists"
else
    fail "styles/app.tcss missing"
fi

# 9. Full build check
echo ""
echo "--- PyInstaller build ---"
if uv run pyinstaller transkript.spec --clean --noconfirm >/dev/null 2>&1; then
    pass "PyInstaller build completed"
else
    fail "PyInstaller build failed"
fi

# Summary
echo ""
echo "=== Summary ==="
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}All checks passed!${NC} Ready to build exe."
    echo ""
    echo "Run: ./build.sh"
    exit 0
else
    echo -e "${RED}$ERRORS check(s) failed.${NC} Fix issues before building."
    exit 1
fi
