#!/usr/bin/env bash
# Build script for transkript executable
# Usage: ./build.sh

set -e

echo "=== Building transkript executable ==="

# Install dev dependencies
echo "Installing dependencies..."
uv sync --group dev

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.spec.bak

# Build with PyInstaller
echo "Building executable..."
uv run pyinstaller transkript.spec --clean --noconfirm

echo ""
echo "=== Build complete ==="
echo "Executable location: dist/transkript/transkript.exe"
echo ""
echo "To distribute:"
echo "  1. Zip the dist/transkript/ folder"
echo "  2. Users extract and run transkript.exe"
echo ""
