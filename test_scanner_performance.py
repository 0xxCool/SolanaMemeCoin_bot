#!/usr/bin/env python3
"""
Scanner Performance Test
Testet den optimierten Scanner für 60 Sekunden
"""
import asyncio
import time
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def test_scanner_performance():
    """Testet Scanner Performance für 60 Sekunden"""
    try:
        # Import Scanner
        from scanner import scanner
        logger.info("✅ Scanner importiert")

        # Start Zeit
        start_time = time.time()
        test_duration = 60  # 60 Sekunden

        logger.info("=" * 70)
        logger.info("🚀 SCANNER PERFORMANCE TEST")
        logger.info("=" * 70)
        logger.info(f"Test-Dauer: {test_duration} Sekunden")
        logger.info(f"Scanner-Modus: HTTP Fallback mit 3 parallelen APIs")
        logger.info("=" * 70)
        logger.info("")

        # Starte Scanner als Background Task
        scanner_task = asyncio.create_task(scanner.start())
        logger.info("✅ Scanner gestartet...")
        logger.info("")

        # Warte Test-Dauer
        await asyncio.sleep(test_duration)

        # Stoppe Scanner
        logger.info("")
        logger.info("⏹️  Stoppe Scanner...")
        scanner.running = False
        await asyncio.sleep(2)

        # Cancel Task falls noch läuft
        if not scanner_task.done():
            scanner_task.cancel()
            try:
                await scanner_task
            except asyncio.CancelledError:
                pass

        # Sammle Stats
        runtime = time.time() - start_time

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 TEST RESULTS")
        logger.info("=" * 70)
        logger.info(f"Runtime:              {runtime:.1f}s")
        logger.info(f"HTTP Requests:        {scanner.stats.get('http_requests', 0)}")
        logger.info(f"Pairs gefunden:       {scanner.stats.get('pairs_found', 0)}")
        logger.info(f"Pairs verarbeitet:    {scanner.stats.get('processed', 0)}")
        logger.info(f"Token Profiles Calls: {scanner.stats.get('api_profiles_calls', 0)}")
        logger.info(f"Solana Pairs Calls:   {scanner.stats.get('api_pairs_calls', 0)}")
        logger.info(f"Search Calls:         {scanner.stats.get('api_search_calls', 0)}")
        logger.info("=" * 70)

        # Berechne Rate
        pairs_per_min = (scanner.stats.get('pairs_found', 0) / runtime) * 60 if runtime > 0 else 0
        logger.info(f"Pairs/Minute:         {pairs_per_min:.1f}")
        logger.info("")

        # Performance-Bewertung
        logger.info("📈 PERFORMANCE VERGLEICH:")
        logger.info("-" * 70)
        logger.info(f"Expected Performance:")
        logger.info(f"  - Parallel HTTP:    10-30 pairs/min")
        logger.info(f"  - Old Sequential:   5-10 pairs/min")
        logger.info("")

        if pairs_per_min >= 10:
            logger.info("✅ EXCELLENT - Scanner läuft optimal!")
        elif pairs_per_min >= 5:
            logger.info("✅ GOOD - Scanner läuft gut")
        else:
            logger.info("⚠️  LOW - Möglicherweise wenig Aktivität auf DexScreener")

        logger.info("=" * 70)
        logger.info("")
        logger.info("💡 HINWEIS:")
        logger.info("Niedrige Pairs/Min können normal sein wenn DexScreener aktuell")
        logger.info("wenig neue Solana-Tokens hat. Das ist keine Scanner-Performance!")
        logger.info("")
        logger.info("✅ Test abgeschlossen!")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Test abgebrochen durch User")
    except Exception as e:
        logger.error(f"❌ Test-Fehler: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            scanner.running = False
            await asyncio.sleep(1)
        except:
            pass

if __name__ == '__main__':
    try:
        asyncio.run(test_scanner_performance())
    except KeyboardInterrupt:
        print("\n✅ Test beendet")
