#!/bin/bash
# Quick start script for Solana Trading Bot

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Run setup.sh first."
    exit 1
fi

# Start bot
echo "🚀 Starting Solana Trading Bot..."
python3 main.py
