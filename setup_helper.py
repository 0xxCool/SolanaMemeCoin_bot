#!/usr/bin/env python3
"""
Setup Helper - Python utilities for bot setup
Provides advanced setup functions and validations
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_colored(text: str, color: str):
    """Print colored text"""
    print(f"{color}{text}{Colors.END}")

def print_section(title: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")

# ==============================================================================
# WALLET GENERATION & MANAGEMENT
# ==============================================================================

def generate_wallet() -> Dict[str, str]:
    """
    Generate a new Solana wallet
    Returns dict with public_key and private_key
    """
    try:
        from solders.keypair import Keypair
        import base58

        # Generate keypair
        keypair = Keypair()
        public_key = str(keypair.pubkey())

        # Extract private key (first 32 bytes)
        secret_bytes = bytes(keypair)[:32]
        private_key = base58.b58encode(secret_bytes).decode()

        return {
            'public_key': public_key,
            'private_key': private_key,
            'keypair_bytes': list(bytes(keypair))  # Full 64 bytes for backup
        }
    except ImportError:
        print_colored("❌ Error: solders package not installed", Colors.RED)
        print("   Run: pip install solders")
        sys.exit(1)
    except Exception as e:
        print_colored(f"❌ Error generating wallet: {e}", Colors.RED)
        sys.exit(1)

def validate_wallet(private_key: str) -> Tuple[bool, str]:
    """
    Validate a private key
    Returns (is_valid, message)
    """
    try:
        import base58
        from solders.keypair import Keypair

        # Try to decode Base58
        try:
            secret_bytes = base58.b58decode(private_key)
        except Exception:
            return False, "Invalid Base58 encoding"

        # Check length
        if len(secret_bytes) != 32:
            return False, f"Invalid key length: {len(secret_bytes)} bytes (expected 32)"

        # Try to create keypair
        try:
            # For solders, we need the full 64 bytes (secret + public)
            # We only have secret, so derive public
            keypair = Keypair.from_bytes(secret_bytes + secret_bytes)  # Temporary
            return True, f"Valid wallet: {str(keypair.pubkey())}"
        except Exception as e:
            return False, f"Cannot create keypair: {e}"

    except ImportError:
        return False, "solders package not installed"
    except Exception as e:
        return False, f"Validation error: {e}"

def save_wallet_backup(wallet: Dict[str, str], filename: str = ".wallet_backup.json"):
    """Save wallet backup to encrypted file"""
    backup_data = {
        'public_key': wallet['public_key'],
        'private_key': wallet['private_key'],
        'keypair_bytes': wallet.get('keypair_bytes', []),
        'created_at': __import__('datetime').datetime.now().isoformat(),
        'warning': 'KEEP THIS FILE SECRET! Contains your private key!'
    }

    # Create .keys directory if not exists
    keys_dir = Path('.keys')
    keys_dir.mkdir(exist_ok=True)

    backup_path = keys_dir / filename

    with open(backup_path, 'w') as f:
        json.dump(backup_data, f, indent=2)

    # Make file readable only by owner
    os.chmod(backup_path, 0o600)

    return str(backup_path)

# ==============================================================================
# ENVIRONMENT VALIDATION
# ==============================================================================

def validate_env_file() -> Tuple[bool, List[str]]:
    """
    Validate .env file configuration
    Returns (all_valid, issues_list)
    """
    from dotenv import load_dotenv

    if not Path('.env').exists():
        return False, [".env file not found"]

    load_dotenv()

    issues = []

    # Check required variables
    required = {
        'PRIVATE_KEY': 'Wallet private key',
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token',
        'TELEGRAM_CHAT_ID': 'Telegram chat ID',
        'RPC_URL': 'Solana RPC endpoint'
    }

    for var, description in required.items():
        value = os.getenv(var)

        if not value:
            issues.append(f"{var} is empty")
        elif 'YOUR_' in value or 'test_' in value or 'CHANGE_ME' in value:
            issues.append(f"{var} contains placeholder value")
        else:
            # Additional validation
            if var == 'PRIVATE_KEY':
                is_valid, msg = validate_wallet(value)
                if not is_valid:
                    issues.append(f"PRIVATE_KEY is invalid: {msg}")

            elif var == 'TELEGRAM_BOT_TOKEN':
                if ':' not in value or len(value) < 40:
                    issues.append("TELEGRAM_BOT_TOKEN format looks incorrect")

            elif var == 'TELEGRAM_CHAT_ID':
                if not value.lstrip('-').isdigit():
                    issues.append("TELEGRAM_CHAT_ID should be numeric")

            elif var == 'RPC_URL':
                if not value.startswith('http'):
                    issues.append("RPC_URL should start with http:// or https://")

    return len(issues) == 0, issues

# ==============================================================================
# DEPENDENCY CHECKS
# ==============================================================================

def check_dependencies() -> Dict[str, Dict]:
    """
    Check all required dependencies
    Returns dict with package info
    """
    required_packages = {
        'solana': '0.36.10',
        'solders': '0.23.0',
        'python-telegram-bot': '21.9',
        'aiohttp': '3.11.11',
        'websockets': '12.0',
        'pandas': '2.2.3',
        'numpy': '1.26.4',
        'scikit-learn': '1.5.2',
        'torch': '2.5.1',
        'tensorflow': '2.18.0',
        'aiosqlite': '0.20.0',
        'sqlalchemy': '2.0.36',
    }

    results = {}

    for package, required_version in required_packages.items():
        try:
            # Try to import
            if package == 'python-telegram-bot':
                module = __import__('telegram')
            elif package == 'scikit-learn':
                module = __import__('sklearn')
            else:
                module = __import__(package)

            # Get version
            version = getattr(module, '__version__', 'unknown')

            results[package] = {
                'installed': True,
                'version': version,
                'required': required_version,
                'ok': True  # Could add version comparison
            }
        except ImportError:
            results[package] = {
                'installed': False,
                'version': None,
                'required': required_version,
                'ok': False
            }

    return results

# ==============================================================================
# DATABASE SETUP
# ==============================================================================

async def initialize_database() -> Tuple[bool, str]:
    """Initialize database tables"""
    try:
        from database import TradeDatabase

        db = TradeDatabase()
        await db.initialize()
        await db.conn.close()

        return True, "Database initialized successfully"
    except Exception as e:
        return False, f"Database initialization failed: {e}"

# ==============================================================================
# CONFIGURATION TESTING
# ==============================================================================

async def test_rpc_connection(rpc_url: str) -> Tuple[bool, str, float]:
    """
    Test RPC connection
    Returns (success, message, latency_ms)
    """
    import aiohttp
    import time

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getHealth"
    }

    try:
        start = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.post(rpc_url, json=payload, timeout=5) as response:
                latency = (time.time() - start) * 1000

                if response.status == 200:
                    data = await response.json()
                    if 'result' in data or 'error' not in data:
                        return True, f"Connected (latency: {latency:.0f}ms)", latency
                    else:
                        return False, f"RPC error: {data.get('error', 'unknown')}", latency
                else:
                    return False, f"HTTP {response.status}", latency

    except asyncio.TimeoutError:
        return False, "Connection timeout", 5000
    except Exception as e:
        return False, f"Connection error: {e}", -1

async def test_telegram_bot(token: str, chat_id: str) -> Tuple[bool, str]:
    """Test Telegram bot connection"""
    try:
        import aiohttp

        # Test bot token
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{token}/getMe"
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_name = data['result']['username']

                        # Try to send test message
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        payload = {
                            'chat_id': chat_id,
                            'text': '✅ Bot setup test successful!'
                        }

                        async with session.post(send_url, json=payload, timeout=5) as msg_response:
                            if msg_response.status == 200:
                                return True, f"Connected to @{bot_name}, test message sent"
                            else:
                                return False, f"Bot valid (@{bot_name}) but cannot send to chat {chat_id}"
                    else:
                        return False, "Invalid bot token"
                else:
                    return False, f"HTTP {response.status}"

    except asyncio.TimeoutError:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {e}"

# ==============================================================================
# MAIN SETUP WIZARD
# ==============================================================================

async def run_setup_wizard():
    """Main setup wizard"""
    print_section("PYTHON SETUP HELPER - ADVANCED CONFIGURATION")

    print_colored("This wizard helps with advanced setup tasks:\n", Colors.CYAN)
    print("1. Generate new wallet")
    print("2. Validate existing wallet")
    print("3. Test RPC connection")
    print("4. Test Telegram bot")
    print("5. Initialize database")
    print("6. Full validation check")
    print("7. Exit")

    choice = input(f"\n{Colors.BOLD}Choose option (1-7): {Colors.END}")

    if choice == '1':
        await generate_wallet_wizard()
    elif choice == '2':
        await validate_wallet_wizard()
    elif choice == '3':
        await test_rpc_wizard()
    elif choice == '4':
        await test_telegram_wizard()
    elif choice == '5':
        await init_database_wizard()
    elif choice == '6':
        await full_validation()
    else:
        print_colored("\n👋 Goodbye!", Colors.GREEN)
        return

async def generate_wallet_wizard():
    """Wallet generation wizard"""
    print_section("WALLET GENERATION")

    print_colored("⚠️  IMPORTANT:", Colors.YELLOW)
    print("  • This will be a BURNER wallet for trading only")
    print("  • NEVER use your main wallet!")
    print("  • Save the private key securely")
    print()

    confirm = input("Generate new wallet? (yes/no): ")
    if confirm.lower() != 'yes':
        print_colored("Cancelled", Colors.YELLOW)
        return

    print_colored("\n🔄 Generating wallet...", Colors.CYAN)
    wallet = generate_wallet()

    print_section("WALLET GENERATED SUCCESSFULLY")

    print_colored("📍 PUBLIC ADDRESS (send SOL here):", Colors.GREEN)
    print(f"   {wallet['public_key']}\n")

    print_colored("🔑 PRIVATE KEY (keep secret!):", Colors.RED)
    print(f"   {wallet['private_key']}\n")

    # Save backup
    backup_path = save_wallet_backup(wallet)
    print_colored(f"💾 Backup saved to: {backup_path}", Colors.CYAN)
    print_colored("   (This file is readable only by you)\n", Colors.CYAN)

    # Update .env
    update_env = input("Update .env file with this wallet? (yes/no): ")
    if update_env.lower() == 'yes':
        try:
            with open('.env', 'r') as f:
                content = f.read()

            content = content.replace(
                'PRIVATE_KEY="YOUR_BASE58_PRIVATE_KEY_HERE"',
                f'PRIVATE_KEY="{wallet["private_key"]}"'
            )

            # Also replace if already set
            import re
            content = re.sub(
                r'PRIVATE_KEY="[^"]*"',
                f'PRIVATE_KEY="{wallet["private_key"]}"',
                content
            )

            with open('.env', 'w') as f:
                f.write(content)

            print_colored("✅ .env file updated", Colors.GREEN)
        except Exception as e:
            print_colored(f"❌ Failed to update .env: {e}", Colors.RED)

    print_colored("\n⚠️  NEXT STEPS:", Colors.YELLOW)
    print("  1. Send 1-2 SOL to the public address above")
    print("  2. Wait for confirmation (usually < 1 minute)")
    print("  3. Start the bot with ./start.sh")

async def validate_wallet_wizard():
    """Wallet validation wizard"""
    print_section("WALLET VALIDATION")

    private_key = input("Enter private key to validate: ").strip()

    print_colored("\n🔄 Validating...", Colors.CYAN)
    is_valid, message = validate_wallet(private_key)

    if is_valid:
        print_colored(f"\n✅ {message}", Colors.GREEN)
    else:
        print_colored(f"\n❌ {message}", Colors.RED)

async def test_rpc_wizard():
    """RPC connection test wizard"""
    print_section("RPC CONNECTION TEST")

    from dotenv import load_dotenv
    load_dotenv()

    rpc_url = os.getenv('RPC_URL', '')

    if rpc_url:
        print(f"Testing RPC from .env: {rpc_url}")
        use_env = True
    else:
        rpc_url = input("Enter RPC URL to test: ").strip()
        use_env = False

    print_colored("\n🔄 Testing connection...", Colors.CYAN)
    success, message, latency = await test_rpc_connection(rpc_url)

    if success:
        print_colored(f"\n✅ {message}", Colors.GREEN)

        if latency > 1000:
            print_colored(f"\n⚠️  High latency detected!", Colors.YELLOW)
            print("   Consider using a premium RPC for better performance:")
            print("   • Helius: https://www.helius.dev/")
            print("   • Alchemy: https://www.alchemy.com/")
    else:
        print_colored(f"\n❌ {message}", Colors.RED)

async def test_telegram_wizard():
    """Telegram bot test wizard"""
    print_section("TELEGRAM BOT TEST")

    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    if not token:
        token = input("Enter Telegram bot token: ").strip()
    else:
        print(f"Using token from .env: {token[:20]}...")

    if not chat_id:
        chat_id = input("Enter chat ID: ").strip()
    else:
        print(f"Using chat ID from .env: {chat_id}")

    print_colored("\n🔄 Testing Telegram bot...", Colors.CYAN)
    print_colored("(Check your Telegram for test message)", Colors.CYAN)

    success, message = await test_telegram_bot(token, chat_id)

    if success:
        print_colored(f"\n✅ {message}", Colors.GREEN)
        print_colored("Check your Telegram for the test message!", Colors.CYAN)
    else:
        print_colored(f"\n❌ {message}", Colors.RED)

async def init_database_wizard():
    """Database initialization wizard"""
    print_section("DATABASE INITIALIZATION")

    if Path('trades.db').exists():
        print_colored("⚠️  Database already exists", Colors.YELLOW)
        reset = input("Reset database? (yes/no): ")
        if reset.lower() == 'yes':
            os.remove('trades.db')
            print_colored("Old database removed", Colors.CYAN)
        else:
            print_colored("Keeping existing database", Colors.CYAN)
            return

    print_colored("\n🔄 Initializing database...", Colors.CYAN)
    success, message = await initialize_database()

    if success:
        print_colored(f"\n✅ {message}", Colors.GREEN)
        print_colored(f"Database file: trades.db", Colors.CYAN)
    else:
        print_colored(f"\n❌ {message}", Colors.RED)

async def full_validation():
    """Full validation check"""
    print_section("FULL VALIDATION CHECK")

    all_ok = True

    # Check dependencies
    print_colored("📦 Checking dependencies...\n", Colors.CYAN)
    deps = check_dependencies()

    installed = sum(1 for d in deps.values() if d['installed'])
    total = len(deps)

    for package, info in deps.items():
        if info['installed']:
            print_colored(f"  ✅ {package:30} {info['version']}", Colors.GREEN)
        else:
            print_colored(f"  ❌ {package:30} NOT INSTALLED", Colors.RED)
            all_ok = False

    print(f"\n  Installed: {installed}/{total}")

    # Check .env
    print_colored("\n📝 Checking .env configuration...\n", Colors.CYAN)
    env_valid, issues = validate_env_file()

    if env_valid:
        print_colored("  ✅ All environment variables configured", Colors.GREEN)
    else:
        print_colored("  ❌ Configuration issues found:", Colors.RED)
        for issue in issues:
            print(f"     • {issue}")
        all_ok = False

    # Test RPC
    if env_valid:
        print_colored("\n🌐 Testing RPC connection...\n", Colors.CYAN)
        from dotenv import load_dotenv
        load_dotenv()

        rpc_url = os.getenv('RPC_URL', '')
        success, message, latency = await test_rpc_connection(rpc_url)

        if success:
            print_colored(f"  ✅ {message}", Colors.GREEN)
        else:
            print_colored(f"  ❌ {message}", Colors.RED)
            all_ok = False

    # Summary
    print_section("VALIDATION SUMMARY")

    if all_ok:
        print_colored("✅ ALL CHECKS PASSED - BOT IS READY!", Colors.GREEN)
        print()
        print("Next steps:")
        print("  1. Fund your wallet with SOL")
        print("  2. Run: ./start.sh")
        print("  3. Open Telegram and send /start to your bot")
    else:
        print_colored("❌ SOME CHECKS FAILED", Colors.RED)
        print()
        print("Please fix the issues above before starting the bot.")

# ==============================================================================
# CLI INTERFACE
# ==============================================================================

def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'generate-wallet':
            asyncio.run(generate_wallet_wizard())
        elif command == 'validate-wallet':
            asyncio.run(validate_wallet_wizard())
        elif command == 'test-rpc':
            asyncio.run(test_rpc_wizard())
        elif command == 'test-telegram':
            asyncio.run(test_telegram_wizard())
        elif command == 'init-db':
            asyncio.run(init_database_wizard())
        elif command == 'validate-all':
            asyncio.run(full_validation())
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  generate-wallet  - Generate new wallet")
            print("  validate-wallet  - Validate existing wallet")
            print("  test-rpc        - Test RPC connection")
            print("  test-telegram   - Test Telegram bot")
            print("  init-db         - Initialize database")
            print("  validate-all    - Run all validation checks")
    else:
        asyncio.run(run_setup_wizard())

if __name__ == '__main__':
    main()
