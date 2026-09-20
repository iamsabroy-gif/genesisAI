#!/usr/bin/env bash
# ==============================================================================
# Project Genesis: macOS Application & DMG Installer Builder
# Creates Genesis.app and an installable Genesis-Installer-<arch>.dmg
# Compatible with Apple Silicon (M1/M2/M3/M4) and Intel Macs
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ARCH="$(uname -m)"
echo "🚀 Building Genesis AI macOS App for architecture: $ARCH"

# Determine Python executable
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
    PYINSTALLER=".venv/bin/pyinstaller"
else
    PYTHON="python3"
    PIP="pip3"
    PYINSTALLER="pyinstaller"
fi

# Ensure build dependencies
if ! command -v "$PYINSTALLER" &> /dev/null && [ ! -f "$PYINSTALLER" ]; then
    echo "📦 Installing PyInstaller..."
    "$PIP" install pyinstaller
fi

# Clean previous build artifacts
echo "🧹 Cleaning previous build artifacts..."
rm -rf build dist/Genesis dist/Genesis.app dist/*.dmg

# Build Genesis.app via PyInstaller
echo "🔨 Compiling Genesis.app with native WebKit bindings..."
"$PYINSTALLER" --noconfirm Genesis.spec

# Verify build succeeded
if [ ! -d "dist/Genesis.app" ]; then
    echo "❌ Build failed: dist/Genesis.app not found."
    exit 1
fi

echo "✅ Genesis.app created successfully!"

# Create DMG Installer
DMG_NAME="Genesis-Installer-${ARCH}.dmg"
STAGING_DIR="dist/dmg_staging"

echo "💿 Packaging $DMG_NAME..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# Copy .app bundle and create /Applications symlink for drag-and-drop install
cp -R dist/Genesis.app "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

# Generate disk image using native hdiutil
hdiutil create -volname "Genesis AI" \
    -srcfolder "$STAGING_DIR" \
    -ov -format UDZO \
    "dist/$DMG_NAME"

rm -rf "$STAGING_DIR"

echo "=============================================================================="
echo "🎉 SUCCESS: Installable macOS package created:"
echo "   📍 File: dist/$DMG_NAME"
echo "   📏 Size: $(du -sh "dist/$DMG_NAME" | cut -f1)"
echo "   💻 Arch: $ARCH"
echo "=============================================================================="
