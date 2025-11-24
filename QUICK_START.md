# 🚀 Quick Start Guide

## Starting the Bot

```bash
./start.sh
```

## Stopping the Bot

```bash
./stop.sh
```

## Check Status

```bash
./status.sh
```

## Re-run Setup

If you need to re-run setup (e.g., to reconfigure or update):

```bash
# Run setup again - it will skip already completed steps
./setup.sh

# To force reset and start fresh
rm .setup_state
./setup.sh
```

## Telegram Commands

Once the bot is running, open Telegram and:

1. Search for your bot (name you gave to @BotFather)
2. Send `/start`
3. You should see the main menu

### Essential Commands

- `/start` - Show main menu
- `/status` - Bot status
- `/dashboard` - Live dashboard
- `/positions` - Show open positions
- `/settings` - Configure parameters
- `/stop` - Stop scanner (positions remain open)

## Configuration

Edit `.env` file to change:
- Wallet private key
- Telegram tokens
- RPC endpoint
- Trading parameters

## Logs

- **bot.log** - Main application log
- **logs/audit.log** - Security audit log
- **trades.db** - Trade history database

## Safety Tips

⚠️ **IMPORTANT:**
1. Start with SMALL amounts (0.01 SOL)
2. Use a BURNER wallet (not your main wallet)
3. Enable AUTO-BUY only after testing
4. Monitor continuously for first 24 hours
5. Set stop-loss limits

## Troubleshooting

### Bot won't start

```bash
# Check Python version (need 3.10+)
python3 --version

# Check .env file
cat .env | grep -v "^#" | grep "="

# Check logs
tail -50 bot.log
```

### No tokens found

1. Lower MIN_SCORE in Settings
2. Check RPC connection
3. Verify WebSocket connectivity

### Transactions failing

1. Check wallet balance: Need >0.5 SOL
2. Increase slippage tolerance
3. Use premium RPC (Helius/Alchemy)

## Getting Help

1. Check README.md for detailed documentation
2. Review logs in bot.log
3. Check GitHub issues

## Emergency Stop

If something goes wrong:

```bash
./stop.sh

# Or force kill
pkill -9 -f "python3 main.py"
```

Then review logs and fix issues before restarting.
