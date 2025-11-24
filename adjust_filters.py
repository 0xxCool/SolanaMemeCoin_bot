#!/usr/bin/env python3
"""
Test und adjust Filter-Settings für mehr Token-Alerts
"""
import sys

print("🔍 Filter Check & Adjustment Tool\n")
print("=" * 60)

# Read current config
try:
    with open('config.py', 'r') as f:
        config_content = f.read()
    
    # Extract current values
    import re
    
    filters = {
        'MIN_SCORE': re.search(r'MIN_SCORE:\s*float\s*=\s*(\d+)', config_content),
        'MIN_VOLUME_USD': re.search(r'MIN_VOLUME_USD:\s*float\s*=\s*(\d+)', config_content),
        'MAX_AGE_MINUTES': re.search(r'MAX_AGE_MINUTES:\s*float\s*=\s*(\d+)', config_content),
        'MIN_HOLDER_COUNT': re.search(r'MIN_HOLDER_COUNT:\s*int\s*=\s*(\d+)', config_content),
    }
    
    print("\n📊 AKTUELLE FILTER:\n")
    for key, match in filters.items():
        if match:
            print(f"  {key:20s}: {match.group(1)}")
    
    print("\n" + "=" * 60)
    print("\n🎯 EMPFOHLENE WERTE (für maximale Token-Findung):\n")
    print(f"  {'MIN_SCORE':20s}: 40  (current: {filters['MIN_SCORE'].group(1) if filters['MIN_SCORE'] else 'N/A'})")
    print(f"  {'MIN_VOLUME_USD':20s}: 500  (current: {filters['MIN_VOLUME_USD'].group(1) if filters['MIN_VOLUME_USD'] else 'N/A'})")
    print(f"  {'MAX_AGE_MINUTES':20s}: 360  (current: {filters['MAX_AGE_MINUTES'].group(1) if filters['MAX_AGE_MINUTES'] else 'N/A'})")
    print(f"  {'MIN_HOLDER_COUNT':20s}: 5  (current: {filters['MIN_HOLDER_COUNT'].group(1) if filters['MIN_HOLDER_COUNT'] else 'N/A'})")
    
    print("\n" + "=" * 60)
    print("\n⚠️  WARNUNG:")
    print("  • Niedrigere Filter = Mehr Alerts aber auch mehr Risiko")
    print("  • Teste erst mit kleinen Trade-Amounts!")
    print("  • Beobachte die Ergebnisse 24h")
    
    print("\n" + "=" * 60)
    
    response = input("\nMöchtest du die Filter auf 'Maximum Finding' setzen? (y/n): ")
    
    if response.lower() == 'y':
        print("\n🔧 Passe Filter an...")
        
        import shutil
        shutil.copy2('config.py', 'config.py.backup_filters')
        print("✅ Backup erstellt: config.py.backup_filters")
        
        # Apply changes
        new_content = config_content
        new_content = re.sub(r'MIN_SCORE:\s*float\s*=\s*\d+', 'MIN_SCORE: float = 40', new_content)
        new_content = re.sub(r'MIN_VOLUME_USD:\s*float\s*=\s*\d+', 'MIN_VOLUME_USD: float = 500', new_content)
        new_content = re.sub(r'MAX_AGE_MINUTES:\s*float\s*=\s*\d+', 'MAX_AGE_MINUTES: float = 360', new_content)
        new_content = re.sub(r'MIN_HOLDER_COUNT:\s*int\s*=\s*\d+', 'MIN_HOLDER_COUNT: int = 5', new_content)
        
        with open('config.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Filter aktualisiert!")
        print("\n📝 NÄCHSTE SCHRITTE:")
        print("  1. Bot neu starten: ./start_optimized.sh restart")
        print("  2. Logs beobachten: ./start_optimized.sh logs")
        print("  3. Nach 10-30 Minuten solltest du Alerts sehen")
        print("\n💡 Falls zu viele Alerts: Filter wieder erhöhen")
        print("   Restore Backup: cp config.py.backup_filters config.py")
    else:
        print("\n✅ Keine Änderungen vorgenommen")

except FileNotFoundError:
    print("❌ config.py nicht gefunden!")
    print("   Bist du im richtigen Verzeichnis?")
    sys.exit(1)
except Exception as e:
    print(f"❌ Fehler: {e}")
    sys.exit(1)