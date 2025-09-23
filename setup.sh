#!/bin/bash

# DPRK Image Capture System - Setup Script

echo "============================================================"
echo "DPRK Image Capture System - Environment Setup"
echo "============================================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed."
    echo "Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv is installed"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
uv pip install -r requirements.txt
echo "✓ Python dependencies installed"

# Install Playwright browsers
echo "Installing Playwright browsers..."
uv run playwright install chromium
echo "✓ Playwright browsers installed"

# Check PostgreSQL
echo "Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL is installed"

    # Try to connect to the database
    if PGPASSWORD=jonathanholmes psql -U postgres -h localhost -d dprk -c "SELECT 1;" &> /dev/null; then
        echo "✓ Database 'dprk' is accessible"
    else
        echo "⚠ Cannot connect to database 'dprk'"
        echo "  Run: python init_database.py"
    fi
else
    echo "❌ PostgreSQL is not installed"
    echo "  Install with: brew install postgresql"
fi

# Check Ollama
echo "Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama server is running"

    # Check for llava model
    if uv run python -c "import requests; r = requests.get('http://localhost:11434/api/tags'); print('llava' in str(r.json()))" | grep -q "True"; then
        echo "✓ llava model is installed"
    else
        echo "⚠ llava model not installed"
        echo "  Installing llava model..."
        ollama pull llava
    fi
else
    echo "⚠ Ollama server is not running"
    echo "  Start with: ollama serve"
fi

# Initialize database if needed
echo ""
echo "Initializing database..."
uv run python init_database.py

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "To run the system:"
echo "1. Ensure Ollama is running: ollama serve"
echo "2. Test with limited queries: uv run python main.py test"
echo "3. Run full pipeline: uv run python main.py"
echo ""