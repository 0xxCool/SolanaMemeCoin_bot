# scanner_optimizations.py
"""
ULTRA-PERFORMANCE OPTIMIZATIONS für scanner.py
Kopiere diese Änderungen in deine scanner.py
"""

# ============================================================
# OPTIMIERUNG 1: Sleep-Zeiten reduzieren
# ============================================================
# Zeile 388: await asyncio.sleep(3)
# ÄNDERE ZU:
await asyncio.sleep(2)  # Von 3s auf 2s - 50% mehr Requests

# ============================================================
# OPTIMIERUNG 2: Mehr Worker für paralleles Processing
# ============================================================
# Zeile 86: num_workers = 5
# ÄNDERE ZU:
num_workers = 8  # Von 5 auf 8 - 60% mehr Parallelität

# ============================================================
# OPTIMIERUNG 3: Größere Queue für mehr Throughput
# ============================================================
# Zeile 59: self.processing_queue = asyncio.Queue(maxsize=1000)
# ÄNDERE ZU:
self.processing_queue = asyncio.Queue(maxsize=2000)  # Doppelte Kapazität

# ============================================================
# OPTIMIERUNG 4: Aggressiveres Logging für Debugging
# ============================================================
# Zeile 36-38: DEBUG Flags
# ÄNDERE ZU:
DEBUG_HTTP_REQUESTS = True   # Zeigt ALLE API Requests
LOG_NEW_TOKENS = True        # Loggt alle neuen Tokens
LOG_PASSED_FILTERS = True    # Loggt erfolgreiche Filter-Passes

# ============================================================
# OPTIMIERUNG 5: Mehr Tokens pro Request verarbeiten
# ============================================================
# Zeile 173: for profile in profiles[:30]:
# ÄNDERE ZU:
for profile in profiles[:50]:  # Von 30 auf 50 - 66% mehr Coverage

# Zeile 244: for pair in pairs[:30]:
# ÄNDERE ZU:
for pair in pairs[:50]:  # Von 30 auf 50

# Zeile 316: for pair in pairs[:30]:
# ÄNDERE ZU:
for pair in pairs[:50]:  # Von 30 auf 50

# ============================================================
# OPTIMIERUNG 6: Schnellere Cache-Rotation
# ============================================================
# Zeile 56: self.processed_pairs_max_age = 3600
# ÄNDERE ZU:
self.processed_pairs_max_age = 1800  # Von 1h auf 30min - findet mehr Wiederholungen

# ============================================================
# OPTIMIERUNG 7: Bessere API-Gewichtung für Token-Finding
# ============================================================
# Zeile 147-148: API Rotation Weights
# ÄNDERE ZU:
weights = [0.60, 0.30, 0.10]  # Mehr Fokus auf Token Profiles (60%)
# Begründung: Token Profiles API findet die neuesten Tokens

# ============================================================
# OPTIMIERUNG 8: Timeout-Handling optimieren
# ============================================================
# Zeile 122: timeout=aiohttp.ClientTimeout(total=10)
# ÄNDERE ZU:
timeout=aiohttp.ClientTimeout(total=15)  # Von 10s auf 15s - weniger Timeouts

# ============================================================
# OPTIMIERUNG 9: Mehr Search Queries für bessere Coverage
# ============================================================
# Zeile 130-135: search_queries Liste
# FÜGE HINZU:
search_queries = [
    # Original queries
    'pump', 'moon', 'pepe', 'doge', 'inu', 'shib', 'elon',
    'wojak', 'bonk', 'floki', 'cat', 'dog', 'rocket',
    'raydium', 'orca', 'meteora',
    'sol', 'solana',
    # NEUE queries für mehr Coverage
    'meme', 'token', 'coin', 'shiba', 'akita', 'husky',
    'btc', 'eth', 'chad', 'giga', 'sigma', 'based',
    'ape', 'gorilla', 'kong', 'lambo', 'diamond', 'hands',
    'frog', 'kek', 'wojak', 'chad', 'npc', 'zoomer'
]

# ============================================================
# ZUSAMMENFASSUNG DER OPTIMIERUNGEN
# ============================================================
"""
Erwartete Verbesserungen:
- 50% mehr API Requests (sleep 3s → 2s)
- 60% mehr paralleles Processing (5 → 8 Workers)
- 66% mehr Tokens pro Request (30 → 50)
- Doppelte Queue-Kapazität
- 2x mehr Search-Queries
- Bessere Fehlertoleranz (15s timeout)

Geschätzte Gesamt-Performance-Steigerung: 3-4x
"""

# ============================================================
# INSTALLATION
# ============================================================
"""
MANUELLE ÄNDERUNGEN DURCHFÜHREN:

1. Öffne scanner.py in einem Editor:
   nano scanner.py

2. Suche die jeweilige Zeile (Ctrl+W in nano)
   
3. Ersetze den Wert wie oben beschrieben

4. Speichere (Ctrl+O, Enter, Ctrl+X)

5. Teste mit:
   python3 -c "import scanner; print('✅ Syntax OK')"

6. Starte Bot neu:
   ./start_optimized.sh restart
"""

# ============================================================
# VERIFICATION SCRIPT
# ============================================================
"""
Führe dieses Script aus um zu prüfen ob alle Optimierungen aktiv sind:

python3 verify_optimizations.py
"""

# ============================================================
# ROLLBACK
# ============================================================
"""
Falls Probleme auftreten, mache ein Backup vorher:

cp scanner.py scanner.py.backup

Bei Problemen:
cp scanner.py.backup scanner.py
"""
