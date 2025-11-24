#!/bin/bash
# Stop script for Solana Trading Bot

echo "🛑 Stopping Solana Trading Bot..."
pkill -f "python3 main.py"

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped"
else
    echo "⚠️  No running bot process found"
fi
