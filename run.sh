#!/bin/bash

# DPRK Image Capture System - Run Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "DPRK Image Capture System - Pipeline Runner"
echo "============================================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed.${NC}"
    echo "Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment not found. Creating...${NC}"
    uv venv
    uv pip install -r requirements.txt
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama is not running${NC}"
    echo "Starting Ollama in background..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Parse command line arguments
case "$1" in
    test)
        echo -e "${GREEN}Running test pipeline (2 queries)...${NC}"
        uv run --no-project python main.py test
        ;;
    basic)
        echo -e "${GREEN}Running basic system tests...${NC}"
        uv run --no-project python test_basic.py
        ;;
    init)
        echo -e "${GREEN}Initializing database...${NC}"
        uv run --no-project python init_database.py
        ;;
    full)
        echo -e "${YELLOW}Running FULL pipeline (all queries)...${NC}"
        echo -e "${YELLOW}This will process all search terms and may take 30-60 minutes.${NC}"
        read -p "Are you sure you want to continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            uv run --no-project python main.py
        else
            echo "Cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 {test|basic|init|full}"
        echo ""
        echo "Commands:"
        echo "  test   - Run pipeline with 2 test queries"
        echo "  basic  - Run basic system tests"
        echo "  init   - Initialize/reset database"
        echo "  full   - Run full pipeline (all queries)"
        echo ""
        echo "Example:"
        echo "  ./run.sh test"
        ;;
esac