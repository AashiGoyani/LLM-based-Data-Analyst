#!/bin/bash
# Create custom Ollama model for text-to-SQL

set -e

MODEL_NAME="sql-analyst"

echo "Creating Ollama model: $MODEL_NAME"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed"
    echo ""
    echo "Install Ollama on macOS:"
    echo "  1. Download from: https://ollama.ai/download"
    echo "  2. Or run: brew install ollama"
    echo "  3. Open the Ollama app from Applications"
    echo ""
    echo "For Linux:"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

# Check if Ollama service is running
if ! ollama list &> /dev/null; then
    echo "Error: Ollama service is not running"
    echo "Start it with: ollama serve"
    exit 1
fi

echo "Pulling base model (this may take a few minutes)..."
ollama pull codellama:7b-instruct

echo ""
echo "Creating custom model from Modelfile..."
cd "$(dirname "$0")"
ollama create $MODEL_NAME -f Modelfile

echo ""
echo "Model created successfully: $MODEL_NAME"
echo ""
echo "Test it:"
echo "  ollama run $MODEL_NAME"
echo ""
echo "Or use the API:"
echo "  curl http://localhost:11434/api/generate -d '{\"model\": \"$MODEL_NAME\", \"prompt\": \"Show average trip distance\"}'"
