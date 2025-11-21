#!/usr/bin/env python3
"""
Comprehensive Component Testing Suite
Tests individual components without requiring full bot startup
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test(name, status, message=""):
    """Print test result"""
    if status:
        symbol = f"{Colors.GREEN}✅{Colors.END}"
        status_text = f"{Colors.GREEN}PASS{Colors.END}"
    else:
        symbol = f"{Colors.RED}❌{Colors.END}"
        status_text = f"{Colors.RED}FAIL{Colors.END}"

    print(f"{symbol} {name:50} [{status_text}] {message}")

def print_section(title):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")

# ==============================================================================
# TEST 1: IMPORTS
# ==============================================================================

def test_imports():
    """Test if all critical modules can be imported"""
    print_section("TEST 1: MODULE IMPORTS")

    modules_to_test = {
        # Core modules
        'config': 'Configuration module',
        'utils': 'Utility functions',
        'validators': 'Input validators',
        'security': 'Security module',
        'rate_limiter': 'API rate limiter',
        'database': 'Database handler',

        # Main components
        'scanner': 'Token scanner',
        'analyzer': 'Token analyzer',
        'trader': 'Trading engine',
        'telegram_bot': 'Telegram bot',

        # Advanced features
        'auto_trader': 'Auto-trader',
        'ml_predictor': 'ML predictor',
        'ai_engine': 'AI engine',
        'mempool_monitor': 'Mempool monitor',
        'integration': 'Integration layer',
        'health': 'Health checks',
    }

    results = {}
    for module, description in modules_to_test.items():
        try:
            __import__(module)
            print_test(f"Import {module}", True, description)
            results[module] = True
        except Exception as e:
            print_test(f"Import {module}", False, f"Error: {str(e)[:40]}")
            results[module] = False

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Import Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 2: CONFIGURATION
# ==============================================================================

def test_configuration():
    """Test configuration loading and validation"""
    print_section("TEST 2: CONFIGURATION")

    results = {}

    # Test config import
    try:
        import config
        print_test("Config module import", True)
        results['import'] = True
    except Exception as e:
        print_test("Config module import", False, str(e))
        results['import'] = False
        return False, results

    # Test config attributes
    required_attrs = [
        'scanner_filters',
        'trading_config',
        'profit_strategy',
        'scoring_weights',
        'monitoring_config',
        'RPC_URL',
        'DEXSCREENER_WSS_URL',
    ]

    for attr in required_attrs:
        has_attr = hasattr(config, attr)
        print_test(f"Config has {attr}", has_attr)
        results[attr] = has_attr

    # Test scanner filters
    try:
        filters = config.scanner_filters
        tests = [
            ('MIN_LIQUIDITY_USD', filters.MIN_LIQUIDITY_USD > 0),
            ('MAX_LIQUIDITY_USD', filters.MAX_LIQUIDITY_USD > filters.MIN_LIQUIDITY_USD),
            ('MIN_AGE_MINUTES', filters.MIN_AGE_MINUTES >= 0),
            ('MIN_HOLDER_COUNT', filters.MIN_HOLDER_COUNT > 0),
        ]

        for test_name, test_result in tests:
            print_test(f"Scanner filter: {test_name}", test_result)
            results[test_name] = test_result

    except Exception as e:
        print_test("Scanner filters validation", False, str(e))
        results['scanner_filters'] = False

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Config Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 3: UTILITIES
# ==============================================================================

def test_utilities():
    """Test utility functions"""
    print_section("TEST 3: UTILITY FUNCTIONS")

    results = {}

    try:
        import utils

        # Test formatting functions
        tests = [
            ('format_number', utils.format_number(1234567.89), '1.23M'),
            ('format_percentage', utils.format_percentage(12.34), '12.34%'),
            ('format_sol_amount', utils.format_sol_amount(1000000000), '1.0000 SOL'),
        ]

        for name, result, expected in tests:
            success = expected in str(result)
            print_test(f"utils.{name}()", success, f"Got: {result}")
            results[name] = success

        # Test validation functions
        try:
            from utils import is_valid_solana_address

            # Test with known invalid addresses
            invalid_tests = [
                ('empty string', is_valid_solana_address(''), False),
                ('too short', is_valid_solana_address('abc'), False),
                ('invalid chars', is_valid_solana_address('!@#$%^&*()'), False),
            ]

            for test_name, result, expected in invalid_tests:
                success = result == expected
                print_test(f"Validation: {test_name}", success)
                results[f'validation_{test_name}'] = success

        except Exception as e:
            print_test("Validation functions", False, str(e))
            results['validation'] = False

    except Exception as e:
        print_test("Utils import", False, str(e))
        return False, results

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Utility Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 4: SECURITY
# ==============================================================================

def test_security():
    """Test security module"""
    print_section("TEST 4: SECURITY")

    results = {}

    try:
        from security import SecurityManager, get_security_manager

        # Test manager instantiation
        try:
            manager = get_security_manager()
            print_test("Security manager instantiation", True)
            results['instantiation'] = True
        except Exception as e:
            print_test("Security manager instantiation", False, str(e))
            results['instantiation'] = False
            return False, results

        # Test encryption/decryption
        try:
            test_data = "test_secret_data_12345"
            encrypted = manager.encrypt(test_data)
            decrypted = manager.decrypt(encrypted)

            success = decrypted == test_data
            print_test("Encryption/Decryption", success)
            results['encryption'] = success
        except Exception as e:
            print_test("Encryption/Decryption", False, str(e))
            results['encryption'] = False

        # Test validation methods
        validation_tests = [
            ('Valid address check', manager.validate_solana_address('11111111111111111111111111111112'), False),
            ('Invalid address check', manager.validate_solana_address('invalid'), False),
            ('Amount validation (valid)', manager.validate_amount(1.5, 0.0, 10.0), True),
            ('Amount validation (too high)', manager.validate_amount(20.0, 0.0, 10.0), False),
        ]

        for test_name, result, expected in validation_tests:
            success = result == expected
            print_test(test_name, success)
            results[test_name] = success

        # Test sanitization
        try:
            dirty_input = '<script>alert("xss")</script>test'
            clean = manager.sanitize_input(dirty_input)
            has_no_tags = '<' not in clean and '>' not in clean
            print_test("Input sanitization", has_no_tags, f"Result: {clean}")
            results['sanitization'] = has_no_tags
        except Exception as e:
            print_test("Input sanitization", False, str(e))
            results['sanitization'] = False

        # Test audit logging
        try:
            manager.audit_log("TEST_EVENT", {"test": "data"}, "test_user")
            log_exists = Path('logs/audit.log').exists()
            print_test("Audit logging", log_exists)
            results['audit_log'] = log_exists
        except Exception as e:
            print_test("Audit logging", False, str(e))
            results['audit_log'] = False

    except Exception as e:
        print_test("Security module import", False, str(e))
        return False, results

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Security Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 5: DATABASE
# ==============================================================================

async def test_database():
    """Test database functionality"""
    print_section("TEST 5: DATABASE")

    results = {}

    try:
        from database import TradeDatabase

        # Test database creation
        test_db_path = "test_trades.db"

        # Clean up old test db
        if Path(test_db_path).exists():
            os.remove(test_db_path)

        db = TradeDatabase(test_db_path)

        try:
            await db.initialize()
            print_test("Database initialization", True)
            results['init'] = True
        except Exception as e:
            print_test("Database initialization", False, str(e))
            results['init'] = False
            return False, results

        # Test trade recording
        try:
            trade_data = {
                'token_address': 'test123456789',
                'symbol': 'TEST',
                'trade_type': 'BUY',
                'amount_sol': 0.1,
                'token_amount': 1000,
                'price': 0.0001,
                'tx_id': 'test_tx_12345',
                'profit_sol': 0,
                'profit_percent': 0,
            }

            trade_id = await db.record_trade(trade_data)
            success = trade_id > 0
            print_test("Record trade", success, f"Trade ID: {trade_id}")
            results['record_trade'] = success
        except Exception as e:
            print_test("Record trade", False, str(e))
            results['record_trade'] = False

        # Test position update
        try:
            position_data = {
                'token_address': 'test123456789',
                'symbol': 'TEST',
                'entry_time': 1234567890.0,
                'entry_price': 0.0001,
                'invested_sol': 0.1,
                'current_amount': 1000,
                'highest_price': 0.00015,
                'lowest_price': 0.00009,
            }

            await db.update_position(position_data)
            print_test("Update position", True)
            results['update_position'] = True
        except Exception as e:
            print_test("Update position", False, str(e))
            results['update_position'] = False

        # Test query
        try:
            trades = await db.get_recent_trades(limit=10)
            success = isinstance(trades, list)
            print_test("Query recent trades", success, f"Found: {len(trades)} trades")
            results['query'] = success
        except Exception as e:
            print_test("Query recent trades", False, str(e))
            results['query'] = False

        # Cleanup
        await db.conn.close()

        # Remove test database
        if Path(test_db_path).exists():
            os.remove(test_db_path)
            print_test("Cleanup test database", True)
        else:
            print_test("Cleanup test database", False, "File not found")

    except Exception as e:
        print_test("Database module import", False, str(e))
        return False, results

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Database Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 6: WALLET FUNCTIONS
# ==============================================================================

def test_wallet_functions():
    """Test wallet-related functions"""
    print_section("TEST 6: WALLET FUNCTIONS")

    results = {}

    try:
        from solders.keypair import Keypair
        import base58

        # Test keypair generation
        try:
            keypair = Keypair()
            public_key = str(keypair.pubkey())
            secret_bytes = bytes(keypair)[:32]
            private_key = base58.b58encode(secret_bytes).decode()

            tests = [
                ('Keypair generation', len(public_key) > 30),
                ('Public key format', public_key.isalnum()),
                ('Private key format', len(private_key) > 40),
                ('Private key Base58', len(base58.b58decode(private_key)) == 32),
            ]

            for test_name, test_result in tests:
                print_test(test_name, test_result)
                results[test_name] = test_result

        except Exception as e:
            print_test("Wallet generation", False, str(e))
            results['generation'] = False

        # Test well-known addresses
        try:
            from solders.pubkey import Pubkey

            # Test SOL address
            sol_address = "So11111111111111111111111111111111111111112"
            try:
                pubkey = Pubkey.from_string(sol_address)
                print_test("Parse SOL address", True, str(pubkey))
                results['parse_sol'] = True
            except Exception as e:
                print_test("Parse SOL address", False, str(e))
                results['parse_sol'] = False

        except Exception as e:
            print_test("Address parsing", False, str(e))
            results['address_parsing'] = False

    except Exception as e:
        print_test("Wallet module import", False, str(e))
        return False, results

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Wallet Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# TEST 7: ASYNC COMPONENTS
# ==============================================================================

async def test_async_components():
    """Test async components without full bot startup"""
    print_section("TEST 7: ASYNC COMPONENTS")

    results = {}

    # Test Scanner initialization (without starting)
    try:
        from scanner import HighPerformanceScanner

        scanner = HighPerformanceScanner()

        tests = [
            ('Scanner instantiation', scanner is not None),
            ('Processing queue exists', hasattr(scanner, 'processing_queue')),
            ('Stats dict exists', hasattr(scanner, 'stats')),
            ('Workers list exists', hasattr(scanner, 'workers')),
        ]

        for test_name, test_result in tests:
            print_test(test_name, test_result)
            results[test_name] = test_result

    except Exception as e:
        print_test("Scanner import", False, str(e))
        results['scanner'] = False

    # Test Analyzer structure
    try:
        from analyzer import EnhancedAnalyzer

        analyzer = EnhancedAnalyzer()

        tests = [
            ('Analyzer instantiation', analyzer is not None),
            ('Cache exists', hasattr(analyzer, 'cache')),
            ('Init task exists', hasattr(analyzer, 'init_task')),
        ]

        for test_name, test_result in tests:
            print_test(test_name, test_result)
            results[test_name] = test_result

    except Exception as e:
        print_test("Analyzer import", False, str(e))
        results['analyzer'] = False

    # Test Trader structure
    try:
        from trader import SmartOrderRouter

        router = SmartOrderRouter()

        tests = [
            ('Router instantiation', router is not None),
            ('DEXs dict exists', hasattr(router, 'dexs')),
            ('Cache exists', hasattr(router, 'quote_cache')),
            ('Stats exists', hasattr(router, 'execution_stats')),
        ]

        for test_name, test_result in tests:
            print_test(test_name, test_result)
            results[test_name] = test_result

    except Exception as e:
        print_test("Trader import", False, str(e))
        results['trader'] = False

    passed = sum(results.values())
    total = len(results)
    print(f"\n{Colors.BOLD}Async Tests: {passed}/{total} passed{Colors.END}")

    return passed == total, results

# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}SOLANA TRADING BOT - COMPONENT TEST SUITE{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

    all_results = {}

    # Run synchronous tests
    sync_tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Utilities", test_utilities),
        ("Security", test_security),
        ("Wallet Functions", test_wallet_functions),
    ]

    for test_name, test_func in sync_tests:
        try:
            passed, results = test_func()
            all_results[test_name] = (passed, results)
        except Exception as e:
            print(f"{Colors.RED}❌ Test '{test_name}' crashed: {e}{Colors.END}")
            all_results[test_name] = (False, {})

    # Run async tests
    async_tests = [
        ("Database", test_database),
        ("Async Components", test_async_components),
    ]

    for test_name, test_func in async_tests:
        try:
            passed, results = await test_func()
            all_results[test_name] = (passed, results)
        except Exception as e:
            print(f"{Colors.RED}❌ Test '{test_name}' crashed: {e}{Colors.END}")
            all_results[test_name] = (False, {})

    # Final summary
    print_section("FINAL SUMMARY")

    total_passed = sum(1 for passed, _ in all_results.values() if passed)
    total_tests = len(all_results)

    for test_name, (passed, results) in all_results.items():
        if passed:
            print(f"{Colors.GREEN}✅ {test_name:30} PASSED{Colors.END}")
        else:
            failed_count = sum(1 for v in results.values() if not v)
            print(f"{Colors.RED}❌ {test_name:30} FAILED ({failed_count} sub-tests){Colors.END}")

    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TOTAL: {total_passed}/{total_tests} test suites passed{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    if total_passed == total_tests:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED - BOT COMPONENTS ARE FUNCTIONAL!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED - REVIEW ISSUES ABOVE{Colors.END}\n")
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
