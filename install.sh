#!/usr/bin/env bash
# ==============================================================================
# Project Genesis: Universal macOS Installer Script
# Works on any Mac (Apple Silicon M1/M2/M3/M4 and Intel x86_64)
# ==============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}======================================================${RESET}"
echo -e "${BOLD}${CYAN}         Project Genesis AI - macOS Installer        ${RESET}"
echo -e "${BOLD}${CYAN}======================================================${RESET}"

ARCH="$(uname -m)"
echo -e "💻 Detected Hardware Architecture: ${GREEN}${ARCH}${RESET}"

# Verify Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}❌ python3 is required but not found. Please install Python 3.10+ via Homebrew or python.org.${RESET}"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "🐍 Detected Python Version: ${GREEN}${PY_VER}${RESET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Setup / Update Isolated Virtual Environment
if [ ! -d ".venv" ]; then
    echo -e "📦 Creating isolated virtual environment in .venv..."
    python3 -m venv .venv
fi

echo -e "📥 Installing dependencies and Genesis package..."
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -e .
.venv/bin/pip install pywebview pyinstaller rich openai pydantic pypdf beautifulsoup4

# 2. Build or link Genesis.app
echo -e "🔨 Building native Genesis.app bundle..."
./scripts/build_dmg.sh

# 3. Create CLI shortcuts in ~/.local/bin or /usr/local/bin
TARGET_BIN="$HOME/.local/bin"
mkdir -p "$TARGET_BIN"

cat << EOF > "$TARGET_BIN/genesis"
#!/usr/bin/env bash
exec "$SCRIPT_DIR/.venv/bin/genesis" "\$@"
EOF
chmod +x "$TARGET_BIN/genesis"

cat << EOF > "$TARGET_BIN/genesis-gui"
#!/usr/bin/env bash
exec "$SCRIPT_DIR/.venv/bin/genesis-gui" "\$@"
EOF
chmod +x "$TARGET_BIN/genesis-gui"

# 4. Prompt to copy Genesis.app to /Applications
if [ -d "dist/Genesis.app" ]; then
    echo -e "📂 Installing Genesis.app to ~/Applications..."
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/Genesis.app"
    cp -R dist/Genesis.app "$HOME/Applications/"
    echo -e "✅ Genesis.app is now available in ${GREEN}~/Applications/Genesis.app${RESET}"
fi

echo -e "\n${BOLD}${GREEN}======================================================${RESET}"
echo -e "${BOLD}${GREEN}🎉 Installation Complete!${RESET}"
echo -e "   • Desktop GUI App : ~/Applications/Genesis.app"
echo -e "   • Terminal CLI    : genesis (in $TARGET_BIN)"
echo -e "   • GUI Terminal cmd: genesis-gui (in $TARGET_BIN)"
echo -e "   • Installable DMG : dist/Genesis-Installer-${ARCH}.dmg"
echo -e "${BOLD}${GREEN}======================================================${RESET}\n"
