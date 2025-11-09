#!/bin/bash
# Script to run the backend server

echo "🚀 Starting ML Trading Bot Backend..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Set PYTHONPATH to the project root
export PYTHONPATH="$(cd .. && pwd):${PYTHONPATH}"

# Initialize database if it doesn't exist
if [ ! -f "trading_predictions.db" ]; then
    echo "🗄️  Initializing database..."
    python database.py
fi

# Run the server
echo "🌐 Starting FastAPI server on http://localhost:8182"
python main.py

