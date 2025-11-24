#!/bin/bash
# Status check script

if pgrep -f "python3 main.py" > /dev/null; then
    echo "✅ Bot is RUNNING"
    echo ""
    echo "Process info:"
    ps aux | grep "python3 main.py" | grep -v grep
else
    echo "⚠️  Bot is NOT running"
fi

# Check log file
if [ -f "bot.log" ]; then
    echo ""
    echo "Latest log entries:"
    tail -10 bot.log
fi
