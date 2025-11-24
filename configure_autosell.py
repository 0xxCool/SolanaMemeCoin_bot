#!/usr/bin/env python3
"""
Auto-Sell Configuration Tool
Einfache Konfiguration von Auto-Sell Parametern
"""
import sys
import re
import shutil

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{CYAN}{'='*60}{NC}")
    print(f"{CYAN}{text}{NC}")
    print(f"{CYAN}{'='*60}{NC}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{NC}")

def print_error(text):
    print(f"{RED}❌ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{NC}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{NC}")

def read_current_settings():
    """Liest aktuelle Auto-Sell Settings"""
    try:
        with open('auto_trader.py', 'r') as f:
            content = f.read()
        
        settings = {
            'enabled': 'False' not in re.search(r'auto_sell_enabled:\s*bool\s*=\s*(\w+)', content).group(0),
            'profit_target': float(re.search(r'auto_sell_profit_target:\s*float\s*=\s*(\d+)', content).group(1)),
            'stop_loss': float(re.search(r'auto_sell_stop_loss:\s*float\s*=\s*(\d+)', content).group(1)),
        }
        return settings
    except:
        return None

def show_current_config(settings):
    """Zeigt aktuelle Konfiguration"""
    print_header("AKTUELLE AUTO-SELL KONFIGURATION")
    
    if settings['enabled']:
        print(f"  Status:         {GREEN}✅ ENABLED{NC}")
    else:
        print(f"  Status:         {RED}❌ DISABLED{NC}")
    
    print(f"  Profit Target:  {settings['profit_target']:.0f}%")
    print(f"  Stop Loss:      {settings['stop_loss']:.0f}%")
    print()

def show_strategies():
    """Zeigt vordefinierte Strategien"""
    print_header("VORDEFINIERTE STRATEGIEN")
    
    strategies = {
        '1': {
            'name': '🟢 Konservativ (Sicher)',
            'profit': 30,
            'stop': 10,
            'desc': 'Schnelle Gewinne, enger Stop-Loss'
        },
        '2': {
            'name': '🟡 Balanced (Standard)',
            'profit': 50,
            'stop': 15,
            'desc': 'Ausgewogene Risk/Reward'
        },
        '3': {
            'name': '🔴 Aggressiv (Moonshot)',
            'profit': 100,
            'stop': 20,
            'desc': 'Große Gewinne, höheres Risiko'
        }
    }
    
    for key, strat in strategies.items():
        print(f"  {key}) {strat['name']}")
        print(f"     Profit Target: {strat['profit']}%")
        print(f"     Stop Loss:     {strat['stop']}%")
        print(f"     → {strat['desc']}")
        print()
    
    print(f"  4) 🎯 Custom Settings")
    print(f"  5) ❌ Disable Auto-Sell")
    print(f"  0) 🚪 Exit")
    print()
    
    return strategies

def apply_settings(enabled, profit_target, stop_loss):
    """Wendet Settings auf auto_trader.py an"""
    try:
        # Backup erstellen
        shutil.copy2('auto_trader.py', 'auto_trader.py.backup_autosell')
        print_success("Backup erstellt: auto_trader.py.backup_autosell")
        
        # Datei lesen
        with open('auto_trader.py', 'r') as f:
            content = f.read()
        
        # Settings ändern
        content = re.sub(
            r'auto_sell_enabled:\s*bool\s*=\s*\w+',
            f'auto_sell_enabled: bool = {enabled}',
            content
        )
        content = re.sub(
            r'auto_sell_profit_target:\s*float\s*=\s*\d+',
            f'auto_sell_profit_target: float = {profit_target}',
            content
        )
        content = re.sub(
            r'auto_sell_stop_loss:\s*float\s*=\s*\d+',
            f'auto_sell_stop_loss: float = {stop_loss}',
            content
        )
        
        # Schreiben
        with open('auto_trader.py', 'w') as f:
            f.write(content)
        
        print_success("Settings aktualisiert!")
        return True
    
    except Exception as e:
        print_error(f"Fehler: {e}")
        return False

def main():
    print_header("🤖 AUTO-SELL CONFIGURATION TOOL")
    
    # Check if file exists
    try:
        settings = read_current_settings()
        if not settings:
            print_error("auto_trader.py nicht gefunden!")
            print_info("Bist du im richtigen Verzeichnis?")
            sys.exit(1)
    except Exception as e:
        print_error(f"Fehler beim Lesen: {e}")
        sys.exit(1)
    
    # Show current config
    show_current_config(settings)
    
    # Show strategies
    strategies = show_strategies()
    
    # Get user choice
    choice = input("Wähle eine Option (0-5): ").strip()
    
    if choice == '0':
        print_info("Abgebrochen")
        sys.exit(0)
    
    elif choice in ['1', '2', '3']:
        strat = strategies[choice]
        print()
        print_info(f"Gewählte Strategie: {strat['name']}")
        print_info(f"Profit Target: {strat['profit']}%")
        print_info(f"Stop Loss: {strat['stop']}%")
        print()
        
        confirm = input("Bestätigen? (y/n): ").strip().lower()
        if confirm == 'y':
            if apply_settings('True', strat['profit'], strat['stop']):
                print()
                print_success("Auto-Sell konfiguriert!")
                print()
                print_info("Nächste Schritte:")
                print("  1. Bot neu starten: ./start_optimized.sh restart")
                print("  2. Logs beobachten: ./start_optimized.sh logs")
                print("  3. Erste Position kaufen und Auto-Sell testen")
        else:
            print_info("Abgebrochen")
    
    elif choice == '4':
        print()
        print_info("Custom Settings")
        print()
        
        try:
            profit = float(input("Profit Target (%)? [30-200]: ").strip())
            stop = float(input("Stop Loss (%)? [5-30]: ").strip())
            
            if not (30 <= profit <= 200):
                print_warning("Profit Target sollte zwischen 30-200% sein")
            if not (5 <= stop <= 30):
                print_warning("Stop Loss sollte zwischen 5-30% sein")
            
            print()
            confirm = input(f"Profit: {profit}%, Stop: {stop}% - OK? (y/n): ").strip().lower()
            
            if confirm == 'y':
                if apply_settings('True', int(profit), int(stop)):
                    print()
                    print_success("Custom Auto-Sell konfiguriert!")
                    print()
                    print_info("Bot neu starten: ./start_optimized.sh restart")
            else:
                print_info("Abgebrochen")
        
        except ValueError:
            print_error("Ungültige Eingabe")
    
    elif choice == '5':
        print()
        confirm = input("Auto-Sell deaktivieren? (y/n): ").strip().lower()
        if confirm == 'y':
            if apply_settings('False', settings['profit_target'], settings['stop_loss']):
                print()
                print_success("Auto-Sell deaktiviert!")
                print()
                print_info("Du musst jetzt manuell über Telegram verkaufen")
                print_info("Bot neu starten: ./start_optimized.sh restart")
        else:
            print_info("Abgebrochen")
    
    else:
        print_error("Ungültige Option")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_info("Abgebrochen")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fehler: {e}")
        sys.exit(1)

