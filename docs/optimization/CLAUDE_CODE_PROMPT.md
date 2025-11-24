# 🤖 Claude Code: Solana Bot Optimierungs-Projekt

**WICHTIG**: Dies ist die Hauptanleitung für Claude Code.  
**Zweck**: Automatische Implementierung aller Optimierungen  
**Repository**: SolanaMemeCoin_bot  
**Geschätzte Dauer**: 2-4 Stunden

---

## 📋 Übersicht

Du bist Claude Code und sollst einen Solana Memecoin Trading Bot optimieren. Dieser Bot hat mehrere Performance-Probleme die systematisch behoben werden müssen.

### Verfügbare Dokumente in docs/optimization/:
1. **EXECUTIVE_SUMMARY.md** - Business Übersicht
2. **SOLANA_BOT_ANALYSE_OPTIMIERUNG.md** - Vollständige technische Analyse
3. **IMPLEMENTIERUNGS_ROADMAP.md** - Step-by-Step Anleitung
4. **scanner_websocket_optimized.py** - Neuer optimierter Scanner
5. **quick_fixes.sh** - Automatisierungs-Script

### Hauptprobleme:
1. ❌ Scanner nutzt HTTP-Polling (18s Latenz) statt WebSocket (0.2s)
2. ❌ 40% redundanter Code (8 tote Dateien)
3. ❌ 4GB RAM durch unnötige Dependencies

### Ziele:
1. ✅ 20x schnellerer Scanner
2. ✅ 40% weniger Code
3. ✅ 80% weniger RAM
4. ✅ Production-ready

---

## 🎯 Deine Aufgaben

### PHASE 0: Quick Wins (PRIORITÄT: KRITISCH)

Diese Phase MUSS zuerst durchgeführt werden!

#### Task 0.1: Backup erstellen
```bash
# Erstelle Backup-Ordner
mkdir -p backups/pre_optimization_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/pre_optimization_$(date +%Y%m%d_%H%M%S)"

# Kopiere alle wichtigen Dateien
cp -r *.py $BACKUP_DIR/
cp -r config.py $BACKUP_DIR/
cp -r requirements.txt $BACKUP_DIR/
cp -r .env $BACKUP_DIR/ 2>/dev/null || true

# Bestätige
echo "✅ Backup erstellt: $BACKUP_DIR"
ls -lh $BACKUP_DIR/
```

**Validierung**:
- [ ] Backup-Ordner existiert
- [ ] Mindestens 30 .py Dateien kopiert
- [ ] config.py vorhanden
- [ ] requirements.txt vorhanden

---

#### Task 0.2: Redundante Dateien löschen

**Diese 8 Dateien MÜSSEN gelöscht werden:**

```python
FILES_TO_DELETE = [
    "scanner.py.backup",
    "config.py.backup", 
    "config.py.backup_filters",
    "dexscreener_http_scanner.py",
    "dexscreener_http_scanner_debug.py",
    "cloudflare_bypass_scanner.py",
    "dexscreener_new_pairs_scanner.py",
    "scanner_optimizations.py"
]

for file in FILES_TO_DELETE:
    if os.path.exists(file):
        os.remove(file)
        print(f"✅ Gelöscht: {file}")
    else:
        print(f"⚠️ Nicht gefunden: {file}")
```

**Validierung**:
- [ ] 8 Dateien gelöscht (oder nicht gefunden)
- [ ] scanner.py existiert noch
- [ ] Bot kann noch importiert werden: `python -c "import scanner"`

---

#### Task 0.3: Scanner optimieren

**Datei**: `scanner.py`

**Änderung 1**: Sleep-Zeit reduzieren (Zeile ~360)
```python
# VORHER:
await asyncio.sleep(15)  # ❌

# NACHHER:
await asyncio.sleep(5)   # ✅

# So findest du die Zeile:
grep -n "await asyncio.sleep(15)" scanner.py
```

**Änderung 2**: Debug-Logs reduzieren (Zeile ~35-40)
```python
# VORHER:
DEBUG_HTTP_REQUESTS = True   # ❌
LOG_NEW_TOKENS = True
LOG_PASSED_FILTERS = True

# NACHHER:
DEBUG_HTTP_REQUESTS = False  # ✅ Nur bei Bedarf
LOG_NEW_TOKENS = True        # ✅ Wichtig behalten
LOG_PASSED_FILTERS = False   # ✅ Zu verbose
```

**Änderung 3**: Parallele API-Calls implementieren (Zeile ~105-150)

Aktuell ist der Code sequential (ein API-Call nach dem anderen).
Das muss parallel werden (alle gleichzeitig).

```python
# VORHER (Sequential):
async def _multi_api_fallback_loop(self):
    while self.running:
        # Zufällige Rotation zwischen 3 APIs
        api_mode = random.choices([0, 1, 2], weights=[0.60, 0.30, 0.10])[0]
        
        if api_mode == 0:
            # API Call 1
            await self._call_token_profiles()
        elif api_mode == 1:
            # API Call 2
            await self._call_solana_pairs()
        elif api_mode == 2:
            # API Call 3
            await self._call_search()
        
        await asyncio.sleep(15)  # Dann warten

# NACHHER (Parallel):
async def _multi_api_fallback_loop(self):
    """Alle APIs parallel abfragen"""
    tasks = [
        asyncio.create_task(self._poll_token_profiles()),
        asyncio.create_task(self._poll_solana_pairs()),
        asyncio.create_task(self._poll_search()),
    ]
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Parallel loop error: {e}")
        for task in tasks:
            task.cancel()

async def _poll_token_profiles(self):
    """Kontinuierliches Polling von Token Profiles"""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    while self.running:
        try:
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Verarbeite Daten (existing logic)
                    profiles = data if isinstance(data, list) else []
                    for profile in profiles[:30]:
                        if profile.get('chainId') == 'solana':
                            # Handle new pair (existing logic)
                            pass
            
            await asyncio.sleep(5)  # 5s statt 15s!
            
        except Exception as e:
            logger.error(f"Token Profiles error: {e}")
            await asyncio.sleep(10)

async def _poll_solana_pairs(self):
    """Kontinuierliches Polling von Solana Pairs"""
    url = "https://api.dexscreener.com/latest/dex/pairs/solana"
    
    while self.running:
        try:
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    # Sortiere nach Alter
                    pairs.sort(key=lambda p: p.get('pairCreatedAt', 0), reverse=True)
                    # Verarbeite neueste 30
                    for pair in pairs[:30]:
                        # Handle new pair (existing logic)
                        pass
            
            await asyncio.sleep(7)  # Leicht höherer Delay
            
        except Exception as e:
            logger.error(f"Solana Pairs error: {e}")
            await asyncio.sleep(10)

async def _poll_search(self):
    """Kontinuierliches Polling mit Search Queries"""
    search_terms = ['pump', 'moon', 'pepe', 'doge', 'sol']
    cycle = 0
    
    while self.running:
        try:
            query = search_terms[cycle % len(search_terms)]
            cycle += 1
            
            url = "https://api.dexscreener.com/latest/dex/search"
            async with self._http_session.get(url, params={'q': query}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    # Verarbeite nur Solana
                    for pair in pairs:
                        if pair.get('chainId') == 'solana':
                            # Handle new pair (existing logic)
                            pass
            
            await asyncio.sleep(10)  # Längerer Delay für Search
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await asyncio.sleep(10)
```

**WICHTIG**: Die bestehende Logik zum Verarbeiten der Pairs (`_handle_new_pair()` etc.) MUSS beibehalten werden. Nur die Loop-Struktur ändert sich von sequential zu parallel.

**Validierung**:
- [ ] `await asyncio.sleep(15)` überall ersetzt durch `5`, `7`, oder `10`
- [ ] `DEBUG_HTTP_REQUESTS = False`
- [ ] Parallele Loop-Struktur implementiert
- [ ] Syntax-Check: `python -m py_compile scanner.py`
- [ ] Import-Check: `python -c "from scanner import scanner"`

---

#### Task 0.4: Config bereinigen

**Datei**: `config.py`

**Aufgabe**: Entferne alte Kommentare und strukturiere neu

```python
# VORHER:
@dataclass
class ScannerFilters:
    # VORHER → NACHHER
    
    # Liquidität - OK, nur leicht anpassen
    MIN_LIQUIDITY_USD: float = 2000        # war: 5000
    MAX_LIQUIDITY_USD: float = 1000000     # war: 500000
    
    # Alter - KRITISCHE ÄNDERUNG
    MIN_AGE_MINUTES: float = 0.1           # war: 0.5
    MAX_AGE_MINUTES: float = 360           # war: 10 ← HAUPTPROBLEM!

# NACHHER:
@dataclass
class ScannerFilters:
    """Scanner Filter - Optimiert für frühe Memecoin-Erkennung"""
    
    # Liquidität
    MIN_LIQUIDITY_USD: float = 2000        # Minimum für Sicherheit
    MAX_LIQUIDITY_USD: float = 1000000     # Maximum für frühe Phase
    
    # Alter (kritisch für Early Entry!)
    MIN_AGE_MINUTES: float = 0.1           # Fast neu (6 Sekunden)
    MAX_AGE_MINUTES: float = 360           # Bis 6 Stunden
```

**Entferne ALLE Kommentare die so aussehen:**
- `# war: XXX`
- `# VORHER → NACHHER`
- `# ← HAUPTPROBLEM!`
- `# KRITISCHE ÄNDERUNG`

**Behalte nur kurze, klare Beschreibungen.**

**Validierung**:
- [ ] Keine "war: XXX" Kommentare mehr
- [ ] Keine "VORHER → NACHHER" Kommentare
- [ ] Werte sind unverändert
- [ ] Syntax-Check: `python -m py_compile config.py`

---

#### Task 0.5: Requirements optimieren

**Erstelle neue Datei**: `requirements.txt`

```python
# Core Dependencies
python-dotenv==1.0.1
aiohttp==3.11.11
websockets==12.0
python-telegram-bot==21.9

# Solana SDK
solana==0.36.10
solders==0.23.0
base58==2.1.1

# Data Processing
pandas==2.2.3
numpy==1.26.4

# Machine Learning (MINIMAL)
scikit-learn==1.5.2
scipy==1.13.1
joblib==1.4.2
aiofiles==24.1.0

# Database
aiosqlite==0.20.0
sqlalchemy==2.0.36

# Monitoring
prometheus-client==0.21.1
colorlog==6.9.0

# Performance
uvloop==0.21.0
orjson==3.10.12

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0

# Code Quality
black==24.10.0
pylint==3.3.2
mypy==1.13.0

# Security
cryptography==44.0.0
bandit==1.8.0
safety==3.2.11
```

**Erstelle Backup**: `requirements-full.txt`

```python
# Full Requirements mit allen ML Libraries
# (Include alles aus requirements.txt PLUS:)

# Deep Learning (optional)
torch==2.5.1
torchvision==0.20.1
tensorflow==2.18.0
keras==3.7.0
```

**WICHTIG**: Frage den User ob er die schweren ML-Libraries (PyTorch/TensorFlow) wirklich braucht!

**Validierung**:
- [ ] requirements.txt erstellt (ohne PyTorch/TF)
- [ ] requirements-full.txt erstellt (mit allem)
- [ ] Alte requirements.txt als requirements.txt.backup gespeichert

---

#### Task 0.6: Testing Phase 0

**Führe folgende Tests durch:**

1. **Syntax-Checks**
```bash
python -m py_compile scanner.py
python -m py_compile config.py
python -m py_compile main.py
```

2. **Import-Tests**
```bash
python -c "from scanner import scanner; print('✅ Scanner import OK')"
python -c "from config import scanner_filters; print('✅ Config import OK')"
python -c "import telegram_bot; print('✅ Telegram import OK')"
```

3. **File-Count Validation**
```bash
# Zähle Python-Dateien
find . -name "*.py" -not -path "./backups/*" -not -path "./.git/*" | wc -l

# Sollte ~34 sein (vorher 42)
```

4. **Code-Zeilen Validation**
```bash
# Zähle Zeilen in scanner.py
wc -l scanner.py
# Sollte ~750 sein (fast unverändert, nur Optimierungen)

# Zähle Zeilen in config.py
wc -l config.py
# Sollte ~280 sein (vorher ~300)
```

**Ausgabe an User:**
```
✅ Phase 0 abgeschlossen!

Zusammenfassung:
- Backup erstellt: backups/pre_optimization_YYYYMMDD_HHMMSS/
- Dateien gelöscht: 8
- scanner.py optimiert: Sleep 15s → 5s, Parallel APIs
- config.py bereinigt: Alte Kommentare entfernt
- requirements.txt: Optimiert (3.8 GB gespart)

Tests:
✅ Alle Syntax-Checks erfolgreich
✅ Alle Imports funktionieren
✅ Bot kann starten

Statistiken:
- Python-Dateien: 42 → 34 (-19%)
- Code-Zeilen: ~11.800 → ~7.200 (-39%)
- Dependencies: 56 → 30 (-46%)

Geschätzte Verbesserungen:
- Scanner Geschwindigkeit: +200% (3x schneller)
- Startup Zeit: -80% (15s → 3s)
- RAM Usage: -80% (4GB → 800MB)

Bereit für Phase 1? (WebSocket Implementation)
[Sage "ja" wenn du weiter machen willst, oder teste erstmal mit: python main.py]
```

---

### PHASE 1: WebSocket Implementation (PRIORITÄT: HOCH)

**WICHTIG**: Starte Phase 1 NUR wenn User "ja" sagt!

#### Task 1.1: Proxy-Konfiguration

**Frage User:**
```
🔐 Proxy-Konfiguration für WebSocket

WebSocket-Verbindungen zu DexScreener können durch Cloudflare blockiert werden.
Für optimale Performance empfehle ich Residential Proxies.

Hast du Proxies verfügbar?

1) Ja, ich habe Proxies (bitte URLs eingeben)
2) Nein, nutze HTTP-Fallback (3x schneller als vorher, aber nicht Echtzeit)
3) Versuche erst direkt ohne Proxies

[Eingabe 1, 2, oder 3]
```

**Wenn User "1" wählt:**
```
Bitte gib deine Proxy URLs ein (Format: http://user:pass@host:port):

Proxy 1: [Eingabe]
Proxy 2: [Eingabe] (optional)
Proxy 3: [Eingabe] (optional)

[Enter wenn fertig]
```

**Speichere Proxies in**: `config.py`

```python
# Am Anfang von config.py hinzufügen:

# ==============================================================================
# PROXY CONFIGURATION (für WebSocket)
# ==============================================================================
ROTATING_PROXIES = [
    # User-provided proxies
    "http://user:pass@proxy1:port",
    "http://user:pass@proxy2:port",
]

# Wenn keine Proxies: leere Liste
ROTATING_PROXIES = []
```

---

#### Task 1.2: Scanner WebSocket Integration

**Option A: Vollständige Integration (EMPFOHLEN)**

Ersetze `scanner.py` komplett mit `docs/optimization/scanner_websocket_optimized.py`:

```bash
# Backup des alten Scanners
cp scanner.py scanner.py.phase0

# Kopiere neuen Scanner
cp docs/optimization/scanner_websocket_optimized.py scanner.py

# Update imports in main.py falls nötig
# (sollte automatisch funktionieren da gleicher Name)
```

**Option B: Hybride Integration (SICHERER)**

Behalte alten Scanner als Fallback:

```python
# main.py - Ändern:

# VORHER:
from scanner import scanner

# NACHHER:
try:
    from scanner_websocket_optimized import scanner
    logger.info("✅ Using optimized WebSocket scanner")
except ImportError:
    from scanner import scanner
    logger.warning("⚠️ Fallback to old scanner")
```

**Kopiere Datei:**
```bash
cp docs/optimization/scanner_websocket_optimized.py ./
```

**Validierung**:
- [ ] scanner_websocket_optimized.py existiert
- [ ] Import funktioniert: `python -c "from scanner_websocket_optimized import scanner"`
- [ ] Keine Syntax-Errors

---

#### Task 1.3: Proxy-Integration in Scanner

**Datei**: `scanner_websocket_optimized.py` oder `scanner.py`

**Finde Zeile ~22-30:**
```python
# ==============================================================================
# PROXY CONFIGURATION
# ==============================================================================
ROTATING_PROXIES = [
    # Format: "http://user:pass@proxy:port"
]
```

**Ersetze durch:**
```python
# ==============================================================================
# PROXY CONFIGURATION
# ==============================================================================
from config import ROTATING_PROXIES  # Import from config
```

**Validierung**:
- [ ] Proxy-Import funktioniert
- [ ] Scanner kann starten

---

#### Task 1.4: Testing WebSocket/Fallback

**Erstelle Test-Script**: `test_scanner.py`

```python
#!/usr/bin/env python3
"""Test Scanner Performance"""
import asyncio
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scanner():
    """Test Scanner Latenz und Funktionalität"""
    try:
        from scanner_websocket_optimized import scanner
        logger.info("✅ Using WebSocket scanner")
    except ImportError:
        from scanner import scanner
        logger.info("⚠️ Using fallback scanner")
    
    logger.info("🚀 Starting scanner test...")
    
    # Start scanner
    start_time = time.time()
    scanner_task = asyncio.create_task(scanner.start())
    
    # Run for 60 seconds
    await asyncio.sleep(60)
    
    # Stop scanner
    scanner.running = False
    await asyncio.sleep(2)
    scanner_task.cancel()
    
    # Stats
    runtime = time.time() - start_time
    pairs_found = scanner.metrics.pairs_processed
    msgs_received = scanner.metrics.messages_received
    
    logger.info(f"""
📊 Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runtime:         {runtime:.1f}s
Pairs Found:     {pairs_found}
Messages:        {msgs_received}
Pairs/Min:       {pairs_found / (runtime / 60):.1f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Expected Performance:
- WebSocket:     50-100 pairs/min
- HTTP Fallback: 10-30 pairs/min
- Old Scanner:   5-10 pairs/min

Status: {'✅ GOOD' if pairs_found > 10 else '⚠️ NEEDS IMPROVEMENT'}
    """)

if __name__ == '__main__':
    asyncio.run(test_scanner())
```

**Führe Test aus:**
```bash
python test_scanner.py
```

**Erwartete Ausgabe:**
```
✅ Using WebSocket scanner
🚀 Starting scanner test...
📡 WebSocket: Verbindungsversuch #1
✅ WebSocket verbunden!
📊 WebSocket: 100 Nachrichten | Latenz: 127.3ms
✨ New Pair [websocket]: PUMP (8f7a2e1d...)
...

📊 Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runtime:         60.0s
Pairs Found:     47
Messages:        856
Pairs/Min:       47.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Expected Performance:
- WebSocket:     50-100 pairs/min
- HTTP Fallback: 10-30 pairs/min
- Old Scanner:   5-10 pairs/min

Status: ✅ GOOD
```

**Validierung**:
- [ ] Scanner startet
- [ ] Keine Errors
- [ ] Pairs werden gefunden
- [ ] Performance ist besser als vorher

---

#### Task 1.5: Performance-Monitoring Integration

**Erstelle**: `monitoring/scanner_metrics.py`

```python
"""Scanner Performance Metrics"""
import time
import logging
from typing import Dict, List
from collections import deque

logger = logging.getLogger(__name__)

class ScannerMetrics:
    """Sammelt und reportet Scanner-Metriken"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history = deque(maxlen=100)
        
    def record_event(self, event_type: str, data: Dict):
        """Zeichnet ein Event auf"""
        self.metrics_history.append({
            'timestamp': time.time(),
            'type': event_type,
            'data': data
        })
    
    def get_stats(self) -> Dict:
        """Berechnet aktuelle Stats"""
        uptime = time.time() - self.start_time
        
        # Count events
        pairs_found = sum(1 for e in self.metrics_history if e['type'] == 'pair_found')
        errors = sum(1 for e in self.metrics_history if e['type'] == 'error')
        
        # Calculate rates
        pairs_per_minute = (pairs_found / uptime) * 60 if uptime > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'pairs_found': pairs_found,
            'errors': errors,
            'pairs_per_minute': pairs_per_minute,
        }
    
    async def report_to_telegram(self):
        """Sendet Stats zu Telegram"""
        try:
            import telegram_bot
            stats = self.get_stats()
            
            message = f"""
📊 Scanner Performance Report

Uptime: {stats['uptime_seconds'] / 60:.1f} min
Pairs Found: {stats['pairs_found']}
Rate: {stats['pairs_per_minute']:.1f}/min
Errors: {stats['errors']}

Status: {'✅ GOOD' if stats['pairs_per_minute'] > 10 else '⚠️ LOW'}
            """
            
            await telegram_bot.send_message(message, important=False)
            
        except Exception as e:
            logger.error(f"Metrics report error: {e}")

# Global instance
metrics = ScannerMetrics()
```

**Integriere in Scanner:**

```python
# In scanner_websocket_optimized.py

from monitoring.scanner_metrics import metrics

# In _handle_new_pair():
metrics.record_event('pair_found', {
    'address': pair_address,
    'source': source
})

# In error handlers:
metrics.record_event('error', {
    'error': str(e),
    'location': 'websocket_loop'
})
```

**Validierung**:
- [ ] monitoring/scanner_metrics.py erstellt
- [ ] Integration in Scanner funktioniert
- [ ] Metriken werden gesammelt

---

#### Task 1.6: Finale Validation Phase 1

**Führe Full-Stack Test durch:**

1. **Start Bot komplett**
```bash
python main.py
```

2. **Check Logs** (in anderem Terminal)
```bash
tail -f bot.log | grep -E "WebSocket|Latency|New Pair|ERROR"
```

3. **Expected Output**:
```
✅ WebSocket verbunden!
✨ New Pair [websocket]: PUMP (8f7a2e1d...)
📊 WebSocket: 100 Nachrichten | Latenz: 127.3ms
✨ New Pair [websocket]: MOON (3d4e5f6a...)
...
```

4. **Performance Test** (nach 5 Minuten)
```bash
# Zähle gefundene Pairs
grep "New Pair" bot.log | wc -l

# Erwarte: 20-50 Pairs in 5 Minuten (4-10/min)
# Vorher: 2-5 Pairs in 5 Minuten
```

5. **Telegram Test**
```
In Telegram:
/dashboard   # Sollte Stats zeigen
/status      # Sollte "✅ WebSocket" oder "🔄 HTTP Fallback" zeigen
```

**Ausgabe an User:**
```
✅ Phase 1 abgeschlossen!

Scanner Status:
- Mode: WebSocket ✅ (oder HTTP Fallback 🔄)
- Latenz: XXXms (Durchschnitt)
- Pairs/Minute: XX.X
- Uptime: XX Minuten
- Errors: X

Performance-Vergleich:
┌─────────────────────────────────────────┐
│           VORHER    NACHHER    DIFF     │
├─────────────────────────────────────────┤
│ Latenz:   18.0s     XXXms      -XX%    │
│ Pairs:    5/min     XX/min     +XX%    │
│ Errors:   XX        X          -XX%    │
└─────────────────────────────────────────┘

Tests:
✅ Bot startet erfolgreich
✅ Scanner läuft stabil
✅ Pairs werden gefunden
✅ Telegram antwortet
✅ Keine kritischen Errors

Empfehlung:
- Lass den Bot 24h laufen
- Überwache Performance
- Bei Problemen: Rollback möglich

Möchtest du weitere Optimierungen? (Phase 2: Refactoring)
[Die meisten Performance-Gewinne sind bereits erreicht. Phase 2 ist optional.]
```

---

## 🔧 Error Handling

### Wenn Probleme auftreten:

#### Error 1: WebSocket 403 (Cloudflare)
```
Symptom: "InvalidStatusCode: 403"

Action:
1. Wechsle zu nächstem Proxy
2. Falls alle Proxies fehlschlagen: HTTP-Fallback
3. HTTP-Fallback ist 3x schneller als vorher → OK!

Message an User:
"⚠️ WebSocket blockiert (Cloudflare), nutze HTTP-Fallback.
Performance: 3x schneller als vorher, aber nicht Echtzeit.
Für Echtzeit: Residential Proxies erforderlich."
```

#### Error 2: Import Errors
```
Symptom: "ImportError: No module named X"

Action:
1. Check requirements.txt installiert
2. Falls nicht: pip install -r requirements.txt
3. Check Python Version ≥ 3.10

Message an User:
"❌ Dependencies fehlen. Bitte ausführen:
pip install -r requirements.txt"
```

#### Error 3: Scanner startet nicht
```
Symptom: Crash beim Scanner-Start

Action:
1. Check Syntax: python -m py_compile scanner.py
2. Check Imports: python -c "from scanner import scanner"
3. Check Logs: tail -f bot.log
4. Falls Crash: Rollback zu Backup

Message an User:
"❌ Scanner-Fehler. Details in bot.log.
Rollback verfügbar? [ja/nein]"
```

#### Error 4: Keine Pairs gefunden
```
Symptom: "0 Pairs in 10 Minuten"

Action:
1. Check API erreichbar: curl https://api.dexscreener.com/latest/dex/pairs/solana
2. Check Rate Limits: grep "429" bot.log
3. Check Filter: config.py → ScannerFilters
4. Falls alles OK: APIs sind evtl. leer (normal bei low activity)

Message an User:
"⚠️ Wenig/keine Pairs gefunden. Mögliche Ursachen:
1. APIs haben aktuell wenig neue Pairs (normal)
2. Rate Limit erreicht (warte 1h)
3. Filter zu strikt (prüfe config.py)

Bot läuft stabil, warte auf neue Pairs."
```

---

## 📊 Success Metrics

### Diese Werte sollst du messen und reporten:

```python
# Nach Phase 0:
phase0_metrics = {
    'files_deleted': 8,
    'code_lines_removed': ~4600,
    'dependencies_removed': ~26,
    'startup_time_before': '15s',
    'startup_time_after': '~3s',
    'improvement': '80%'
}

# Nach Phase 1:
phase1_metrics = {
    'scanner_mode': 'WebSocket' or 'HTTP Fallback',
    'latency_before': '18000ms',
    'latency_after': 'XXXms',
    'pairs_per_min_before': '5-10',
    'pairs_per_min_after': 'XX-XX',
    'improvement': 'XX%'
}
```

---

## 🎯 Finale Ausgabe

### Nach erfolgreichem Abschluss beider Phasen:

```
🎉 Solana Bot Optimierung ABGESCHLOSSEN!

═══════════════════════════════════════════════════════════════

PHASE 0: Quick Wins ✅
- 8 redundante Dateien entfernt
- Scanner optimiert (3x schneller)
- Config bereinigt
- Dependencies optimiert (4GB → 800MB)

PHASE 1: WebSocket Implementation ✅
- WebSocket Scanner integriert
- Latenz: 18s → XXXms
- Performance: +XXX%
- Monitoring aktiv

═══════════════════════════════════════════════════════════════

PERFORMANCE VERGLEICH:

Metrik              Vorher    Nachher    Verbesserung
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scanner Latenz:     18.0s     XXXms      -XX%
Pairs/Minute:       5-10      XX-XX      +XX%
Startup Zeit:       15s       3s         -80%
RAM Usage:          4.0GB     800MB      -80%
Code-Zeilen:        11.8k     7.2k       -39%
Dependencies:       56        30         -46%

═══════════════════════════════════════════════════════════════

NÄCHSTE SCHRITTE:

1. ✅ Bot läuft stabil
2. 📊 Überwache Performance für 24h
3. 💰 Tracke Profit-Verbesserung
4. 🔧 Bei Bedarf: Weitere Optimierungen

BACKUP LOCATION:
backups/pre_optimization_YYYYMMDD_HHMMSS/

Bei Problemen: Rollback mit:
cp -r backups/pre_optimization_YYYYMMDD_HHMMSS/* .

═══════════════════════════════════════════════════════════════

Geschätzte ROI:
- Mehr Trades: +6/Tag
- Mehr Profit: +$1.800/Monat
- Jährlich: +$21.600

Zeit investiert: ~4 Stunden
ROI: $540/Stunde

🚀 OPTIMIERUNG ERFOLGREICH!
```

---

## 🎓 Wichtige Hinweise

### Für dich als Claude Code:

1. **Vorsichtig sein bei:**
   - Bestehender Logik in scanner.py
   - Imports die von anderen Modulen genutzt werden
   - .env Variablen
   - Database-Schemas

2. **IMMER Backup machen vor:**
   - Datei-Löschungen
   - Großen Änderungen
   - Integration neuer Module

3. **Nach jedem Task validieren:**
   - Syntax-Checks
   - Import-Tests
   - Grundfunktionalität

4. **User informieren über:**
   - Jeden wichtigen Schritt
   - Potenzielle Risiken
   - Erwartete Änderungen
   - Test-Ergebnisse

5. **Rollback bereit halten:**
   - Backup-Location dokumentieren
   - Rollback-Commands bereit
   - Git-Commits regelmäßig

### Bei Unsicherheiten:

- **Frage den User** bevor du kritische Änderungen machst
- **Erkläre** was du tun wirst
- **Warne** bei Risiken
- **Biete Alternativen** wenn möglich

---

## ✅ Finale Checkliste

### Vor dem Start:
- [ ] Alle Dokumente gelesen
- [ ] User-Bestätigung erhalten
- [ ] Repository-Struktur verstanden

### Phase 0:
- [ ] Backup erstellt
- [ ] 8 Dateien gelöscht
- [ ] scanner.py optimiert
- [ ] config.py bereinigt
- [ ] requirements.txt optimiert
- [ ] Alle Tests erfolgreich
- [ ] User informiert

### Phase 1:
- [ ] User möchte Phase 1
- [ ] Proxy-Config abgefragt
- [ ] WebSocket Scanner integriert
- [ ] Tests durchgeführt
- [ ] Monitoring aktiv
- [ ] Performance gemessen
- [ ] User informiert

### Abschluss:
- [ ] Finale Stats erstellt
- [ ] Performance-Vergleich dokumentiert
- [ ] Backup-Location dokumentiert
- [ ] Nächste Schritte erklärt
- [ ] Rollback-Anleitung gegeben

---

**Status**: ✅ Anleitung komplett  
**Bereit für**: Automatische Implementierung  
**Geschätzte Dauer**: 2-4 Stunden  
**Erfolgsrate**: >95% bei korrekter Ausführung  

**Los geht's! 🚀**
