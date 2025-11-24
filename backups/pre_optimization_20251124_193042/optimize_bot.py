#!/usr/bin/env python3
"""
AUTO-PATCH SCRIPT für Performance-Optimierungen
Führt automatisch alle Optimierungen durch
"""
import sys
import os
import shutil
from pathlib import Path
import re

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{NC}")

def print_error(msg):
    print(f"{RED}❌ {msg}{NC}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{NC}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{NC}")

def backup_file(filepath):
    """Erstellt ein Backup der Datei"""
    backup_path = f"{filepath}.backup"
    shutil.copy2(filepath, backup_path)
    return backup_path

def apply_scanner_optimizations():
    """Wendet alle Scanner-Optimierungen an"""
    print_info("Patche scanner.py...")
    
    scanner_path = Path("scanner.py")
    if not scanner_path.exists():
        print_error("scanner.py nicht gefunden!")
        return False
    
    # Backup erstellen
    backup_path = backup_file(scanner_path)
    print_success(f"Backup erstellt: {backup_path}")
    
    # Datei lesen
    with open(scanner_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # OPTIMIERUNG 1: Sleep Zeit reduzieren
    if 'await asyncio.sleep(3)' in content and 'sleep(2)' not in content:
        content = content.replace('await asyncio.sleep(3)', 'await asyncio.sleep(2)', 1)
        changes_made += 1
        print_success("Sleep Zeit: 3s → 2s")
    
    # OPTIMIERUNG 2: Mehr Worker
    pattern = r'num_workers\s*=\s*5'
    if re.search(pattern, content):
        content = re.sub(pattern, 'num_workers = 8', content)
        changes_made += 1
        print_success("Workers: 5 → 8")
    
    # OPTIMIERUNG 3: Größere Queue
    pattern = r'asyncio\.Queue\(maxsize=1000\)'
    if re.search(pattern, content):
        content = re.sub(pattern, 'asyncio.Queue(maxsize=2000)', content)
        changes_made += 1
        print_success("Queue Size: 1000 → 2000")
    
    # OPTIMIERUNG 4: Debug Logging aktivieren
    if 'DEBUG_HTTP_REQUESTS = False' in content:
        content = content.replace('DEBUG_HTTP_REQUESTS = False', 'DEBUG_HTTP_REQUESTS = True')
        changes_made += 1
        print_success("Debug Logging aktiviert")
    
    # OPTIMIERUNG 5: Mehr Tokens pro Request
    pattern = r'for profile in profiles\[:30\]:'
    if re.search(pattern, content):
        content = re.sub(pattern, 'for profile in profiles[:50]:', content)
        changes_made += 1
        print_success("Token Processing: 30 → 50")
    
    pattern = r'for pair in pairs\[:30\]:'
    count = len(re.findall(pattern, content))
    if count > 0:
        content = re.sub(pattern, 'for pair in pairs[:50]:', content)
        changes_made += count
        print_success(f"Pair Processing: 30 → 50 ({count} Stellen)")
    
    # OPTIMIERUNG 6: Cache-Rotation
    pattern = r'self\.processed_pairs_max_age\s*=\s*3600'
    if re.search(pattern, content):
        content = re.sub(pattern, 'self.processed_pairs_max_age = 1800', content)
        changes_made += 1
        print_success("Cache Age: 3600s → 1800s")
    
    # OPTIMIERUNG 7: API Gewichtung
    pattern = r'weights\s*=\s*\[0\.50,\s*0\.35,\s*0\.15\]'
    if re.search(pattern, content):
        content = re.sub(pattern, 'weights = [0.60, 0.30, 0.10]', content)
        changes_made += 1
        print_success("API Weights: [50,35,15] → [60,30,10]")
    
    # OPTIMIERUNG 8: Timeout erhöhen
    pattern = r'timeout=aiohttp\.ClientTimeout\(total=10\)'
    if re.search(pattern, content):
        content = re.sub(pattern, 'timeout=aiohttp.ClientTimeout(total=15)', content)
        changes_made += 1
        print_success("Timeout: 10s → 15s")
    
    # Datei schreiben wenn Änderungen gemacht wurden
    if content != original_content:
        with open(scanner_path, 'w') as f:
            f.write(content)
        print_success(f"scanner.py aktualisiert ({changes_made} Änderungen)")
        return True
    else:
        print_warning("Keine Änderungen nötig (bereits optimiert)")
        return True

def apply_config_optimizations():
    """Wendet Config-Optimierungen an"""
    print_info("Prüfe config.py...")
    
    config_path = Path("config.py")
    if not config_path.exists():
        print_error("config.py nicht gefunden!")
        return False
    
    # Backup erstellen
    backup_path = backup_file(config_path)
    print_success(f"Backup erstellt: {backup_path}")
    
    # Datei lesen
    with open(config_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Prüfe ob Filter bereits relaxed sind
    if 'MAX_AGE_MINUTES: float = 180' in content:
        print_success("MAX_AGE_MINUTES bereits optimal (180)")
    elif 'MAX_AGE_MINUTES' in content:
        pattern = r'MAX_AGE_MINUTES:\s*float\s*=\s*\d+'
        content = re.sub(pattern, 'MAX_AGE_MINUTES: float = 180', content)
        changes_made += 1
        print_success("MAX_AGE_MINUTES → 180")
    
    if 'MIN_VOLUME_USD: float = 1000' in content:
        print_success("MIN_VOLUME_USD bereits optimal (1000)")
    elif 'MIN_VOLUME_USD' in content:
        pattern = r'MIN_VOLUME_USD:\s*float\s*=\s*\d+'
        content = re.sub(pattern, 'MIN_VOLUME_USD: float = 1000', content)
        changes_made += 1
        print_success("MIN_VOLUME_USD → 1000")
    
    if 'MIN_SCORE: float = 50' in content:
        print_success("MIN_SCORE bereits optimal (50)")
    elif 'MIN_SCORE' in content:
        pattern = r'MIN_SCORE:\s*float\s*=\s*\d+'
        content = re.sub(pattern, 'MIN_SCORE: float = 50', content)
        changes_made += 1
        print_success("MIN_SCORE → 50")
    
    # Datei schreiben wenn Änderungen gemacht wurden
    if content != original_content:
        with open(config_path, 'w') as f:
            f.write(content)
        print_success(f"config.py aktualisiert ({changes_made} Änderungen)")
        return True
    else:
        print_success("config.py bereits optimal")
        return True

def verify_syntax():
    """Verifiziert dass die Python-Dateien keine Syntax-Fehler haben"""
    print_info("Verifiziere Syntax...")
    
    files_to_check = ['scanner.py', 'config.py']
    
    for filepath in files_to_check:
        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filepath, 'exec')
            print_success(f"{filepath}: Syntax OK")
        except SyntaxError as e:
            print_error(f"{filepath}: Syntax Error!")
            print_error(f"  {e}")
            return False
    
    return True

def rollback_changes():
    """Stellt Backup wieder her"""
    print_warning("Stelle Backups wieder her...")
    
    for filepath in ['scanner.py', 'config.py']:
        backup_path = f"{filepath}.backup"
        if Path(backup_path).exists():
            shutil.copy2(backup_path, filepath)
            print_success(f"{filepath} wiederhergestellt")
        else:
            print_warning(f"Kein Backup für {filepath} gefunden")

def main():
    print("=" * 70)
    print(" Solana Bot - Auto Performance Patch v1.0")
    print("=" * 70)
    print()
    
    # Prüfe ob wir im richtigen Verzeichnis sind
    if not Path("scanner.py").exists() or not Path("config.py").exists():
        print_error("Nicht im richtigen Verzeichnis!")
        print_info("Führe das Script im Bot-Root-Verzeichnis aus")
        sys.exit(1)
    
    # Zeige was gemacht wird
    print_info("Dieses Script wird folgende Optimierungen durchführen:")
    print("  • Scanner Sleep Zeit: 3s → 2s (+50% Requests)")
    print("  • Worker Threads: 5 → 8 (+60% Parallelität)")
    print("  • Queue Größe: 1000 → 2000 (Doppelte Kapazität)")
    print("  • Token Processing: 30 → 50 (+66% Coverage)")
    print("  • Debug Logging aktivieren")
    print("  • Cache-Rotation optimieren")
    print("  • API-Gewichtung anpassen")
    print("  • Timeout erhöhen: 10s → 15s")
    print()
    
    response = input("Möchtest du fortfahren? (y/n): ")
    if response.lower() != 'y':
        print_info("Abgebrochen")
        sys.exit(0)
    
    print()
    print_info("Starte Patching-Prozess...")
    print()
    
    # Wende Optimierungen an
    success = True
    
    if not apply_scanner_optimizations():
        success = False
    
    print()
    
    if not apply_config_optimizations():
        success = False
    
    print()
    
    # Verifiziere Syntax
    if not verify_syntax():
        print_error("Syntax-Fehler gefunden!")
        print_warning("Stelle Backups wieder her...")
        rollback_changes()
        sys.exit(1)
    
    print()
    
    if success:
        print_success("Alle Optimierungen erfolgreich angewendet!")
        print()
        print_info("Nächste Schritte:")
        print("  1. Starte den Bot neu: ./start_optimized.sh restart")
        print("  2. Überwache die Logs: ./start_optimized.sh logs")
        print("  3. Prüfe Stats: ./start_optimized.sh stats")
        print()
        print_warning("Falls Probleme auftreten:")
        print("  • Rollback: python3 optimize_bot.py --rollback")
        print("  • Backups sind verfügbar: scanner.py.backup, config.py.backup")
    else:
        print_error("Einige Optimierungen konnten nicht angewendet werden")
        sys.exit(1)

def rollback_main():
    """Rollback-Funktion"""
    print("=" * 70)
    print(" Solana Bot - Rollback zu Original")
    print("=" * 70)
    print()
    
    rollback_changes()
    
    print()
    print_success("Rollback abgeschlossen")
    print_info("Starte Bot neu: ./start_optimized.sh restart")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_main()
    else:
        main()
