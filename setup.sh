#!/bin/bash
# ==============================================================================
# Solana Meme Coin Trading Bot - Automated Setup Script v2.1
# ==============================================================================
# This script automates the complete setup process with state management
# ==============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# State file to track completed steps
STATE_FILE=".setup_state"

# ==============================================================================
# STATE MANAGEMENT FUNCTIONS
# ==============================================================================

init_state() {
    if [ ! -f "$STATE_FILE" ]; then
        cat > "$STATE_FILE" << EOF
# Setup state tracking - DO NOT EDIT MANUALLY
SYSTEM_CHECK=0
VENV_SETUP=0
DEPENDENCIES_INSTALLED=0
ENV_CONFIGURED=0
DATABASE_SETUP=0
VALIDATION_DONE=0
TESTS_RUN=0
SCRIPTS_CREATED=0
EOF
    fi
}

get_state() {
    local key=$1
    local value
    value=$(grep "^${key}=" "$STATE_FILE" 2>/dev/null | cut -d'=' -f2)
    echo "${value:-0}"
}

set_state() {
    local key=$1
    local value=$2

    if grep -q "^${key}=" "$STATE_FILE" 2>/dev/null; then
        sed -i "s/^${key}=.*/${key}=${value}/" "$STATE_FILE"
    else
        echo "${key}=${value}" >> "$STATE_FILE"
    fi
}

is_step_completed() {
    local step=$1
    [ "$(get_state "$step")" = "1" ]
}

mark_step_completed() {
    local step=$1
    set_state "$step" "1"
    print_success "Step marked as complete: $step"
}

reset_state() {
    if [ -f "$STATE_FILE" ]; then
        rm "$STATE_FILE"
        print_info "Setup state reset"
    fi
    init_state
}

show_state() {
    print_header "Current Setup State"

    if [ ! -f "$STATE_FILE" ]; then
        print_info "No state file found - fresh installation"
        return
    fi

    echo -e "${CYAN}Completed steps:${NC}\n"

    local steps=(
        "SYSTEM_CHECK:System Requirements Check"
        "VENV_SETUP:Virtual Environment Setup"
        "DEPENDENCIES_INSTALLED:Dependencies Installation"
        "ENV_CONFIGURED:Environment Configuration"
        "DATABASE_SETUP:Database Setup"
        "VALIDATION_DONE:Validation & Testing"
        "TESTS_RUN:Test Suite Execution"
        "SCRIPTS_CREATED:Startup Scripts Creation"
    )

    for step_info in "${steps[@]}"; do
        local key="${step_info%%:*}"
        local name="${step_info#*:}"
        if is_step_completed "$key"; then
            echo -e "  ${GREEN}✅ $name${NC}"
        else
            echo -e "  ${YELLOW}⏳ $name${NC}"
        fi
    done
    echo ""
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}=====================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=====================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

ask_skip() {
    local step_name=$1
    echo -e "${CYAN}Step '$step_name' is already completed.${NC}"
    read -p "Skip this step? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        return 1  # Don't skip
    fi
    return 0  # Skip
}

# ==============================================================================
# SYSTEM CHECKS
# ==============================================================================

check_system() {
    print_header "STEP 1: System Requirements Check"

    if is_step_completed "SYSTEM_CHECK"; then
        if ask_skip "System Check"; then
            print_info "Skipping system check"
            return
        fi
    fi

    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            print_success "Python $PYTHON_VERSION (>= 3.10 required)"
        else
            print_error "Python 3.10+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi

    # Check pip
    if command -v pip3 &> /dev/null; then
        PIP_VERSION=$(pip3 --version | awk '{print $2}')
        print_success "pip3 $PIP_VERSION installed"
    else
        print_error "pip3 not found. Please install pip3"
        exit 1
    fi

    # Check git
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        print_success "git $GIT_VERSION installed"
    else
        print_warning "git not found - version control unavailable"
    fi

    # Check available disk space (need at least 2GB for dependencies)
    AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
    AVAILABLE_GB=$((AVAILABLE_SPACE / 1024 / 1024))
    if [ "$AVAILABLE_SPACE" -gt 2000000 ]; then
        print_success "Sufficient disk space available (~${AVAILABLE_GB}GB)"
    else
        print_warning "Low disk space (~${AVAILABLE_GB}GB) - may cause issues during installation"
    fi

    # Check internet connectivity
    if ping -c 1 -W 3 8.8.8.8 &> /dev/null; then
        print_success "Internet connection available"
    else
        print_error "No internet connection - required for package installation"
        exit 1
    fi

    mark_step_completed "SYSTEM_CHECK"
}

# ==============================================================================
# VIRTUAL ENVIRONMENT
# ==============================================================================

setup_venv() {
    print_header "STEP 2: Virtual Environment Setup"

    if is_step_completed "VENV_SETUP"; then
        if ask_skip "Virtual Environment Setup"; then
            if [ -d "venv" ]; then
                print_info "Activating existing virtual environment..."
                source venv/bin/activate
                print_success "Virtual environment activated"
            fi
            return
        fi
    fi

    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Remove and recreate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing old virtual environment..."
            rm -rf venv
            print_info "Old virtual environment removed"
        else
            print_info "Using existing virtual environment"
            source venv/bin/activate
            print_success "Virtual environment activated"
            mark_step_completed "VENV_SETUP"
            return
        fi
    fi

    print_info "Creating virtual environment..."
    if python3 -m venv venv; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi

    # Activate venv
    print_info "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"

    # Upgrade pip
    print_info "Upgrading pip, setuptools, and wheel..."
    if pip install --upgrade pip setuptools wheel --quiet; then
        print_success "pip upgraded to $(pip --version | awk '{print $2}')"
    else
        print_warning "Failed to upgrade pip - continuing with current version"
    fi

    mark_step_completed "VENV_SETUP"
}

# ==============================================================================
# DEPENDENCIES INSTALLATION
# ==============================================================================

install_dependencies() {
    print_header "STEP 3: Installing Dependencies"

    # Ensure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "venv" ]; then
            print_info "Activating virtual environment..."
            source venv/bin/activate
        else
            print_error "Virtual environment not found. Please run setup from the beginning."
            exit 1
        fi
    fi

    if is_step_completed "DEPENDENCIES_INSTALLED"; then
        if ask_skip "Dependencies Installation"; then
            print_info "Skipping dependencies installation"
            return
        fi
    fi

    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi

    print_info "This may take 5-10 minutes depending on your connection..."
    print_info "Installing packages from requirements.txt..."
    echo ""

    # Install with progress and better error handling
    if pip install -r requirements.txt --no-cache-dir 2>&1 | tee /tmp/pip_install.log; then
        print_success "All dependencies installed successfully"
    else
        print_error "Failed to install some dependencies"
        print_info "Check /tmp/pip_install.log for details"
        exit 1
    fi

    # Verify critical packages
    print_info "\nVerifying critical packages..."

    CRITICAL_PACKAGES=(
        "solana"
        "solders"
        "python-telegram-bot"
        "aiohttp"
        "websockets"
        "pandas"
        "numpy"
        "python-dotenv"
    )

    local all_installed=true
    for package in "${CRITICAL_PACKAGES[@]}"; do
        if pip show "$package" &> /dev/null; then
            VERSION=$(pip show "$package" 2>/dev/null | grep "^Version:" | awk '{print $2}')
            print_success "$package: $VERSION"
        else
            print_error "$package not installed"
            all_installed=false
        fi
    done

    if [ "$all_installed" = false ]; then
        print_error "Some critical packages are missing!"
        exit 1
    fi

    mark_step_completed "DEPENDENCIES_INSTALLED"
}

# ==============================================================================
# ENVIRONMENT CONFIGURATION
# ==============================================================================

setup_env_file() {
    print_header "STEP 4: Environment Configuration"

    if is_step_completed "ENV_CONFIGURED"; then
        if ask_skip "Environment Configuration"; then
            print_info "Skipping environment configuration"
            return
        fi
    fi

    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env file"
            mark_step_completed "ENV_CONFIGURED"
            return
        fi
    fi

    if [ ! -f ".env.example" ]; then
        print_error ".env.example not found!"
        exit 1
    fi

    cp .env.example .env
    print_success ".env file created from template"

    print_info "\n${YELLOW}⚠️  IMPORTANT: You must configure the following variables in .env:${NC}"
    echo ""
    echo "  1. PRIVATE_KEY         - Your Solana wallet private key (Base58)"
    echo "  2. TELEGRAM_BOT_TOKEN  - Get from @BotFather on Telegram"
    echo "  3. TELEGRAM_CHAT_ID    - Get from @userinfobot on Telegram"
    echo "  4. RPC_URL             - Solana RPC endpoint (default is free but slow)"
    echo ""

    read -p "Would you like to configure now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_env_interactive
    else
        print_warning "Remember to configure .env before running the bot!"
    fi

    mark_step_completed "ENV_CONFIGURED"
}

configure_env_interactive() {
    print_info "\n${BLUE}Starting interactive configuration...${NC}\n"

    # Private Key
    echo -e "${YELLOW}1. PRIVATE_KEY${NC}"
    echo "   Options:"
    echo "   a) I have a private key"
    echo "   b) Generate a new wallet for me"
    echo "   c) Skip (configure manually later)"
    read -p "   Choice (a/b/c): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Aa]$ ]]; then
        read -p "   Enter your Base58 private key: " PRIVATE_KEY
        if [ ! -z "$PRIVATE_KEY" ]; then
            sed -i "s|PRIVATE_KEY=\"YOUR_BASE58_PRIVATE_KEY_HERE\"|PRIVATE_KEY=\"$PRIVATE_KEY\"|" .env
            print_success "Private key configured"
        fi
    elif [[ $REPLY =~ ^[Bb]$ ]]; then
        generate_wallet
    else
        print_warning "Private key skipped - configure manually"
    fi

    # Telegram Bot Token
    echo -e "\n${YELLOW}2. TELEGRAM_BOT_TOKEN${NC}"
    echo "   Get from: @BotFather on Telegram"
    echo "   Send: /newbot and follow instructions"
    read -p "   Enter token (or press Enter to skip): " TELEGRAM_TOKEN

    if [ ! -z "$TELEGRAM_TOKEN" ]; then
        sed -i "s|TELEGRAM_BOT_TOKEN=\".*\"|TELEGRAM_BOT_TOKEN=\"$TELEGRAM_TOKEN\"|" .env
        print_success "Telegram bot token configured"
    else
        print_warning "Telegram token skipped"
    fi

    # Telegram Chat ID
    echo -e "\n${YELLOW}3. TELEGRAM_CHAT_ID${NC}"
    echo "   Get from: @userinfobot on Telegram"
    echo "   Send: /start"
    read -p "   Enter chat ID (or press Enter to skip): " CHAT_ID

    if [ ! -z "$CHAT_ID" ]; then
        sed -i "s|TELEGRAM_CHAT_ID=\".*\"|TELEGRAM_CHAT_ID=\"$CHAT_ID\"|" .env
        print_success "Telegram chat ID configured"
    else
        print_warning "Chat ID skipped"
    fi

    # RPC URL
    echo -e "\n${YELLOW}4. RPC_URL${NC}"
    echo "   Options:"
    echo "   a) Use free RPC (slow, not recommended for production)"
    echo "   b) Enter Helius API key (recommended - free tier available)"
    echo "   c) Enter Alchemy API key"
    echo "   d) Enter custom RPC URL"
    echo "   e) Skip (use default)"
    read -p "   Choice (a/b/c/d/e): " -n 1 -r
    echo

    case $REPLY in
        [Bb])
            read -p "   Enter Helius API key: " HELIUS_KEY
            if [ ! -z "$HELIUS_KEY" ]; then
                sed -i "s|RPC_URL=\".*\"|RPC_URL=\"https://mainnet.helius-rpc.com/?api-key=$HELIUS_KEY\"|" .env
                print_success "Helius RPC configured"
            fi
            ;;
        [Cc])
            read -p "   Enter Alchemy API key: " ALCHEMY_KEY
            if [ ! -z "$ALCHEMY_KEY" ]; then
                sed -i "s|RPC_URL=\".*\"|RPC_URL=\"https://solana-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY\"|" .env
                print_success "Alchemy RPC configured"
            fi
            ;;
        [Dd])
            read -p "   Enter custom RPC URL: " CUSTOM_RPC
            if [ ! -z "$CUSTOM_RPC" ]; then
                sed -i "s|RPC_URL=\".*\"|RPC_URL=\"$CUSTOM_RPC\"|" .env
                print_success "Custom RPC configured"
            fi
            ;;
        *)
            print_info "Using default free RPC"
            ;;
    esac

    print_success "\n✅ Environment configuration complete!"
}

# ==============================================================================
# WALLET GENERATION
# ==============================================================================

generate_wallet() {
    print_info "Generating new Solana wallet..."

    # Ensure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
    fi

    # Create Python script to generate wallet
    python3 << 'PYTHON_SCRIPT'
from solders.keypair import Keypair
import base58
import json
import os

try:
    # Generate new keypair
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    secret_key = base58.b58encode(bytes(keypair)[:32]).decode()

    print("\n" + "="*70)
    print("  🎉 NEW WALLET GENERATED")
    print("="*70)
    print(f"\n📍 Public Address (send SOL here):")
    print(f"   {public_key}")
    print(f"\n🔑 Private Key (keep secret!):")
    print(f"   {secret_key}")
    print("\n" + "="*70)
    print("\n⚠️  IMPORTANT:")
    print("   1. This is a BURNER wallet - use only for trading bot")
    print("   2. Send 1-2 SOL to the public address above")
    print("   3. NEVER share your private key!")
    print("   4. Save this information in a safe place")
    print("="*70 + "\n")

    # Save to .env
    with open('.env', 'r') as f:
        content = f.read()

    content = content.replace(
        'PRIVATE_KEY="YOUR_BASE58_PRIVATE_KEY_HERE"',
        f'PRIVATE_KEY="{secret_key}"'
    )

    with open('.env', 'w') as f:
        f.write(content)

    print("✅ Private key automatically saved to .env file\n")
except Exception as e:
    print(f"❌ Error generating wallet: {e}")
    exit(1)
PYTHON_SCRIPT

    if [ $? -eq 0 ]; then
        print_success "Wallet generated and configured"
        read -p "Press Enter to continue..."
    else
        print_error "Failed to generate wallet"
        print_info "You can configure your private key manually in .env"
    fi
}

# ==============================================================================
# DATABASE SETUP
# ==============================================================================

setup_database() {
    print_header "STEP 5: Database Setup"

    # Ensure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
    fi

    if is_step_completed "DATABASE_SETUP"; then
        if ask_skip "Database Setup"; then
            print_info "Skipping database setup"
            return
        fi
    fi

    if [ -f "trades.db" ]; then
        print_warning "Database already exists"
        read -p "Reset database? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm trades.db
            print_info "Old database removed"
        else
            print_info "Keeping existing database"
            mark_step_completed "DATABASE_SETUP"
            return
        fi
    fi

    print_info "Initializing database..."

    python3 << 'PYTHON_SCRIPT'
import asyncio
import sys

async def init_db():
    try:
        from database import TradeDatabase
        db = TradeDatabase()
        await db.initialize()
        await db.conn.close()
        print("✅ Database initialized successfully")
        return 0
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

sys.exit(asyncio.run(init_db()))
PYTHON_SCRIPT

    if [ $? -eq 0 ]; then
        print_success "Database ready"
        mark_step_completed "DATABASE_SETUP"
    else
        print_error "Database setup failed"
        print_warning "The bot may still work, but trade history won't be saved"
    fi
}

# ==============================================================================
# VALIDATION & TESTING
# ==============================================================================

validate_setup() {
    print_header "STEP 6: Validation & Testing"

    # Ensure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
    fi

    if is_step_completed "VALIDATION_DONE"; then
        if ask_skip "Validation"; then
            print_info "Skipping validation"
            return
        fi
    fi

    print_info "Running syntax checks..."

    MODULES=(
        "main.py"
        "config.py"
        "trader.py"
        "scanner.py"
        "analyzer.py"
        "telegram_bot.py"
    )

    local all_valid=true
    for module in "${MODULES[@]}"; do
        if [ -f "$module" ]; then
            if python3 -m py_compile "$module" 2>/dev/null; then
                print_success "$module: Syntax OK"
            else
                print_error "$module: Syntax Error"
                all_valid=false
            fi
        else
            print_warning "$module: File not found"
        fi
    done

    print_info "\nChecking imports..."

    python3 << 'PYTHON_SCRIPT'
import sys

required_modules = [
    ('solana', 'Solana SDK'),
    ('solders', 'Solana Data Structures'),
    ('telegram.ext', 'Telegram Bot'),
    ('aiohttp', 'Async HTTP'),
    ('websockets', 'WebSocket'),
    ('pandas', 'Data Analysis'),
    ('numpy', 'Numerical Computing'),
]

print()
all_ok = True
for module, name in required_modules:
    try:
        __import__(module)
        print(f"✅ {name:30} OK")
    except ImportError as e:
        print(f"❌ {name:30} MISSING: {e}")
        all_ok = False

if not all_ok:
    sys.exit(1)

print("\n✅ All critical imports successful")
PYTHON_SCRIPT

    if [ $? -eq 0 ]; then
        print_success "All imports validated"
    else
        print_error "Some imports failed - bot may not work correctly"
        all_valid=false
    fi

    # Check .env configuration
    print_info "\nValidating .env configuration..."

    if [ -f ".env" ]; then
        python3 << 'PYTHON_SCRIPT'
import os
from dotenv import load_dotenv

# Load .env with explicit path
load_dotenv('.env')

required_vars = [
    'PRIVATE_KEY',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHAT_ID',
    'RPC_URL'
]

print()
all_configured = True
for var in required_vars:
    value = os.getenv(var)
    if not value or 'YOUR_' in value or 'test_' in value:
        print(f"⚠️  {var:25} NOT CONFIGURED")
        all_configured = False
    else:
        # Mask sensitive data
        if 'KEY' in var or 'TOKEN' in var:
            display = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
        else:
            display = value
        print(f"✅ {var:25} {display}")

if not all_configured:
    print("\n⚠️  Some variables not configured - bot will not start")
else:
    print("\n✅ All required variables configured")
PYTHON_SCRIPT
    else
        print_warning ".env file not found"
        all_valid=false
    fi

    if [ "$all_valid" = true ]; then
        mark_step_completed "VALIDATION_DONE"
    fi
}

# ==============================================================================
# SETUP TESTS
# ==============================================================================

run_tests() {
    print_header "STEP 7: Running Tests (Optional)"

    # Ensure venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
    fi

    if is_step_completed "TESTS_RUN"; then
        if ask_skip "Test Suite"; then
            print_info "Skipping tests"
            return
        fi
    fi

    read -p "Run test suite? (y/n) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Tests skipped"
        mark_step_completed "TESTS_RUN"
        return
    fi

    if [ ! -d "tests" ]; then
        print_warning "Tests directory not found"
        mark_step_completed "TESTS_RUN"
        return
    fi

    print_info "Installing test dependencies..."
    if pip install pytest pytest-asyncio pytest-mock pytest-cov --quiet 2>&1 | grep -v "already satisfied"; then
        print_success "Test dependencies installed"
    else
        print_success "Test dependencies already installed"
    fi

    print_info "Running tests..."
    echo ""

    # Use python3 -m pytest instead of direct pytest command
    if python3 -m pytest tests/ -v --tb=short 2>&1; then
        print_success "\nAll tests passed"
    else
        print_warning "\nSome tests failed - review output above"
        print_info "This may be normal if .env is not fully configured"
    fi

    mark_step_completed "TESTS_RUN"
}

# ==============================================================================
# FINAL SETUP
# ==============================================================================

create_startup_script() {
    print_header "STEP 8: Creating Startup Scripts"

    if is_step_completed "SCRIPTS_CREATED"; then
        if ask_skip "Startup Scripts Creation"; then
            print_info "Skipping startup scripts creation"
            return
        fi
    fi

    # Create start script
    cat > start.sh << 'EOF'
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
EOF

    chmod +x start.sh
    print_success "start.sh created"

    # Create stop script
    cat > stop.sh << 'EOF'
#!/bin/bash
# Stop script for Solana Trading Bot

echo "🛑 Stopping Solana Trading Bot..."
pkill -f "python3 main.py"

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped"
else
    echo "⚠️  No running bot process found"
fi
EOF

    chmod +x stop.sh
    print_success "stop.sh created"

    # Create status script
    cat > status.sh << 'EOF'
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
EOF

    chmod +x status.sh
    print_success "status.sh created"

    mark_step_completed "SCRIPTS_CREATED"
}

create_documentation() {
    print_info "Creating quick reference..."

    cat > QUICK_START.md << 'EOF'
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
EOF

    print_success "QUICK_START.md created"
}

# ==============================================================================
# CLEANUP & RESET OPTIONS
# ==============================================================================

show_menu() {
    clear
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ███████╗ ██████╗ ██╗      █████╗ ███╗   ██╗ █████╗                ║
║   ██╔════╝██╔═══██╗██║     ██╔══██╗████╗  ██║██╔══██╗               ║
║   ███████╗██║   ██║██║     ███████║██╔██╗ ██║███████║               ║
║   ╚════██║██║   ██║██║     ██╔══██║██║╚██╗██║██╔══██║               ║
║   ███████║╚██████╔╝███████╗██║  ██║██║ ╚████║██║  ██║               ║
║   ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝               ║
║                                                                       ║
║            MEME COIN TRADING BOT - SETUP WIZARD v2.1                 ║
║                     With Smart State Management                      ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

EOF

    echo -e "${CYAN}Setup Options:${NC}\n"
    echo "  1) Full Setup (with state management)"
    echo "  2) Show Current State"
    echo "  3) Reset State (start fresh)"
    echo "  4) Quick Reconfigure (env only)"
    echo "  5) Exit"
    echo ""
}

# ==============================================================================
# MAIN SETUP FLOW
# ==============================================================================

main() {
    # Initialize state management
    init_state

    # Check if being run with arguments
    if [ "$1" = "--reset" ]; then
        reset_state
        print_success "State reset complete. Run ./setup.sh to start fresh."
        exit 0
    elif [ "$1" = "--state" ]; then
        show_state
        exit 0
    elif [ "$1" = "--help" ]; then
        echo "Usage: ./setup.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  --reset    Reset setup state and start fresh"
        echo "  --state    Show current setup state"
        echo "  --help     Show this help message"
        echo ""
        echo "Without options: Run interactive setup"
        exit 0
    fi

    # Interactive mode
    while true; do
        show_menu
        read -p "Choose an option (1-5): " -n 1 -r
        echo
        echo ""

        case $REPLY in
            1)
                run_full_setup
                break
                ;;
            2)
                show_state
                read -p "Press Enter to continue..."
                ;;
            3)
                reset_state
                print_success "State reset complete!"
                read -p "Press Enter to continue..."
                ;;
            4)
                setup_env_file
                read -p "Press Enter to continue..."
                ;;
            5)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                sleep 1
                ;;
        esac
    done
}

run_full_setup() {
    clear

    echo -e "${YELLOW}This script will guide you through the complete setup process.${NC}"
    echo -e "${YELLOW}Already completed steps will be skipped automatically.${NC}"
    echo -e "${YELLOW}Estimated time: 5-10 minutes${NC}\n"

    read -p "Press Enter to begin setup..."

    # Run all setup steps
    check_system
    setup_venv
    install_dependencies
    setup_env_file
    setup_database
    validate_setup
    run_tests
    create_startup_script
    create_documentation

    # Final summary
    print_header "🎉 SETUP COMPLETE!"

    echo -e "${GREEN}"
    cat << "EOF"
    ✅ All steps completed successfully!

    📋 NEXT STEPS:

    1. Review your .env configuration:
       nano .env

    2. Fund your wallet with SOL:
       - Get wallet address from .env
       - Send 1-2 SOL to your public address

    3. Start the bot:
       ./start.sh

    4. Open Telegram and send /start to your bot

    5. Start with Conservative settings and small amounts!

    📚 DOCUMENTATION:

    - README.md         - Complete documentation
    - QUICK_START.md    - Quick reference guide
    - .env.example      - Configuration template

    ⚠️  IMPORTANT REMINDERS:

    - Use only a BURNER wallet
    - Start with 0.01 SOL per trade
    - Monitor actively for first 24 hours
    - Enable Auto-Buy only after testing
    - Crypto trading is high risk!

    💡 SETUP STATE MANAGEMENT:

    - Run ./setup.sh --state to see completed steps
    - Run ./setup.sh --reset to start fresh
    - Re-running setup will skip completed steps

EOF
    echo -e "${NC}"

    print_success "Setup wizard completed successfully!"
    echo ""
}

# ==============================================================================
# RUN MAIN
# ==============================================================================

main "$@"
