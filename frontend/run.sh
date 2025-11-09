#!/bin/bash
# Script to run the frontend development server

echo "🚀 Starting ML Trading Bot Frontend..."

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run development server
echo "🌐 Starting Vite dev server on http://localhost:5155"
npm run dev

