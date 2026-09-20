#!/usr/bin/env bash
# ==============================================================================
# Project Genesis: Automatic Setup for XHToken/Spark-X2.5-4B in Ollama
# Downloads Q4_K_M GGUF from Hugging Face and creates the 'spark-4b' model
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MODEL_NAME="spark-4b"
GGUF_FILE="Spark-X2.5-4B-Q4_K_M.gguf"
DOWNLOAD_URL="https://huggingface.co/abenzerps/Spark-X2.5-4B-GGUF/resolve/main/Spark-X2.5-4B-Q4_K_M.gguf"

echo "⚡ Setting up Spark-X2.5-4B for Ollama..."

# 1. Download GGUF if not already present
if [ ! -f "$GGUF_FILE" ]; then
    echo "📥 Downloading $GGUF_FILE (approx 2.6 GB)..."
    curl -L -C - --progress-bar -o "$GGUF_FILE" "$DOWNLOAD_URL"
    echo "✅ Download complete."
else
    echo "✓ Found existing $GGUF_FILE ($(du -sh "$GGUF_FILE" | cut -f1))"
fi

# 2. Verify Ollama is running
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed or not in PATH. Please install Ollama from https://ollama.com"
    exit 1
fi

echo "🔨 Creating Ollama model '$MODEL_NAME' from Modelfile.spark..."
ollama create "$MODEL_NAME" -f Modelfile.spark

echo "=============================================================================="
echo "🎉 SUCCESS: '$MODEL_NAME' is registered in Ollama!"
echo "   • Run interactive test : ollama run $MODEL_NAME"
echo "   • Switch inside Genesis: /model $MODEL_NAME"
echo "=============================================================================="
