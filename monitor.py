#!/usr/bin/env python3
"""
Solana Bot - Live Performance Monitor
Zeigt Echtzeit-Statistiken und Performance-Metriken
"""
import os
import sys
import time
import json
import re
from datetime import datetime, timedelta
from collections import deque, Counter
import curses

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

class BotMonitor:
    def __init__(self, log_file="logs/bot.log"):
        self.log_file = log_file
        self.stats = {
            'pairs_found': 0,
            'passed_filters': 0,
            'trades_executed': 0,
            'errors': 0,
            'warnings': 0,
            'api_requests': 0,
            'last_pair': None,
            'last_trade': None,
            'uptime': 0,
            'start_time': None
        }
        self.events = deque(maxlen=100)
        self.tokens_per_minute = deque(maxlen=60)
        self.last_update = time.time()
        
    def parse_log_line(self, line):
        """Parsed eine Log-Zeile und extrahiert Informationen"""
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # Pairs gefunden
        if 'Neues Pair gefunden' in line or '✨ SEARCH: Neues Pair' in line:
            self.stats['pairs_found'] += 1
            token_match = re.search(r'Pair gefunden:\s*(\w+)', line)
            if token_match:
                self.stats['last_pair'] = {
                    'symbol': token_match.group(1),
                    'time': timestamp
                }
                self.events.append({
                    'type': 'pair_found',
                    'symbol': token_match.group(1),
                    'time': timestamp
                })
        
        # Filter bestanden
        if 'TRADE SIGNAL' in line or '⚡ TRADE SIGNAL' in line:
            self.stats['passed_filters'] += 1
            self.events.append({
                'type': 'filter_passed',
                'time': timestamp
            })
        
        # Trades
        if 'Trade erfolgreich' in line or '✅ Trade' in line:
            self.stats['trades_executed'] += 1
            self.stats['last_trade'] = timestamp
            self.events.append({
                'type': 'trade',
                'time': timestamp
            })
        
        # Errors
        if 'ERROR' in line or '❌' in line:
            self.stats['errors'] += 1
        
        # Warnings
        if 'WARNING' in line or '⚠️' in line:
            self.stats['warnings'] += 1
        
        # API Requests
        if 'HTTP Request' in line or 'API' in line:
            self.stats['api_requests'] += 1
    
    def read_logs(self):
        """Liest neue Log-Einträge"""
        if not os.path.exists(self.log_file):
            return
        
        try:
            with open(self.log_file, 'r') as f:
                # Gehe zum Ende - 5000 Zeilen
                f.seek(0, 2)
                file_size = f.tell()
                
                # Lese letzte ~5000 Zeilen
                chunk_size = min(file_size, 500000)
                f.seek(max(0, file_size - chunk_size))
                
                lines = f.readlines()
                
                # Verarbeite Zeilen
                for line in lines[-1000:]:  # Nur letzte 1000
                    self.parse_log_line(line)
        except Exception as e:
            pass  # Silent fail
    
    def get_health_status(self):
        """Prüft Health-Check Endpoint"""
        if not HAS_REQUESTS:
            return None
        
        try:
            response = requests.get('http://localhost:8000/health', timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def calculate_rates(self):
        """Berechnet Raten pro Minute/Stunde"""
        now = time.time()
        elapsed = now - self.last_update
        
        if elapsed >= 60:  # Alle 60 Sekunden
            pairs_per_min = self.stats['pairs_found']
            self.tokens_per_minute.append(pairs_per_min)
            self.last_update = now
        
        # Durchschnitte
        avg_per_min = sum(self.tokens_per_minute) / len(self.tokens_per_minute) if self.tokens_per_minute else 0
        
        return {
            'pairs_per_min': avg_per_min,
            'pairs_per_hour': avg_per_min * 60
        }
    
    def draw_dashboard(self, stdscr):
        """Zeichnet das Dashboard mit curses"""
        curses.curs_set(0)  # Verstecke Cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(1000)  # Update alle 1 Sekunde
        
        # Farben
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Header
            title = "🤖 SOLANA BOT - LIVE MONITOR"
            stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(0, (width - len(title)) // 2, title)
            stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # Timestamp
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stdscr.addstr(1, (width - len(now)) // 2, now)
            
            # Separator
            stdscr.addstr(2, 0, "═" * width)
            
            row = 4
            
            # === PERFORMANCE METRICS ===
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(row, 2, "📊 PERFORMANCE METRICS")
            stdscr.attroff(curses.A_BOLD)
            row += 2
            
            rates = self.calculate_rates()
            
            metrics = [
                f"Pairs Found:      {self.stats['pairs_found']:>6}",
                f"Filter Passed:    {self.stats['passed_filters']:>6}",
                f"Trades Executed:  {self.stats['trades_executed']:>6}",
                f"API Requests:     {self.stats['api_requests']:>6}",
                "",
                f"Pairs/Minute:     {rates['pairs_per_min']:>6.1f}",
                f"Pairs/Hour:       {rates['pairs_per_hour']:>6.0f}",
            ]
            
            for metric in metrics:
                if metric:
                    stdscr.addstr(row, 4, metric)
                row += 1
            
            row += 1
            
            # === STATUS ===
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(row, 2, "🔋 STATUS")
            stdscr.attroff(curses.A_BOLD)
            row += 2
            
            # Health Check
            health = self.get_health_status()
            if health:
                health_status = "🟢 HEALTHY" if health.get('status') == 'healthy' else "🔴 UNHEALTHY"
                stdscr.attron(curses.color_pair(1))
            else:
                health_status = "⚪ OFFLINE"
                stdscr.attron(curses.color_pair(3))
            
            stdscr.addstr(row, 4, f"Health Check:     {health_status}")
            stdscr.attroff(curses.color_pair(1))
            stdscr.attroff(curses.color_pair(3))
            row += 1
            
            # Errors & Warnings
            if self.stats['errors'] > 0:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(row, 4, f"Errors:           {self.stats['errors']:>6}")
                stdscr.attroff(curses.color_pair(2))
            else:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(row, 4, "Errors:                 0")
                stdscr.attroff(curses.color_pair(1))
            row += 1
            
            if self.stats['warnings'] > 0:
                stdscr.attron(curses.color_pair(3))
                stdscr.addstr(row, 4, f"Warnings:         {self.stats['warnings']:>6}")
                stdscr.attroff(curses.color_pair(3))
            else:
                stdscr.addstr(row, 4, "Warnings:               0")
            row += 2
            
            # === LAST ACTIVITY ===
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(row, 2, "⚡ LAST ACTIVITY")
            stdscr.attroff(curses.A_BOLD)
            row += 2
            
            if self.stats['last_pair']:
                stdscr.addstr(row, 4, f"Last Pair:        {self.stats['last_pair']['symbol']}")
                row += 1
                stdscr.addstr(row, 4, f"                  {self.stats['last_pair']['time']}")
                row += 1
            else:
                stdscr.addstr(row, 4, "Last Pair:        None")
                row += 2
            
            if self.stats['last_trade']:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(row, 4, f"Last Trade:       {self.stats['last_trade']}")
                stdscr.attroff(curses.color_pair(1))
                row += 1
            else:
                stdscr.addstr(row, 4, "Last Trade:       None")
                row += 1
            
            row += 1
            
            # === RECENT EVENTS ===
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(row, 2, "📜 RECENT EVENTS (Last 10)")
            stdscr.attroff(curses.A_BOLD)
            row += 2
            
            recent_events = list(self.events)[-10:]
            recent_events.reverse()
            
            for event in recent_events:
                if row >= height - 4:
                    break
                
                event_type = event['type']
                event_time = event.get('time', 'N/A')
                
                if event_type == 'pair_found':
                    icon = "🔍"
                    text = f"Pair Found: {event.get('symbol', 'Unknown')}"
                    color = curses.color_pair(4)
                elif event_type == 'filter_passed':
                    icon = "✅"
                    text = "Filter Passed"
                    color = curses.color_pair(1)
                elif event_type == 'trade':
                    icon = "💰"
                    text = "Trade Executed"
                    color = curses.color_pair(1) | curses.A_BOLD
                else:
                    icon = "•"
                    text = event_type
                    color = 0
                
                stdscr.attron(color)
                display_text = f"{icon} {event_time} - {text}"
                if len(display_text) > width - 6:
                    display_text = display_text[:width-9] + "..."
                stdscr.addstr(row, 4, display_text)
                stdscr.attroff(color)
                row += 1
            
            # === FOOTER ===
            footer = "Press 'q' to quit | 'r' to refresh | Updating every 1s"
            stdscr.addstr(height - 2, 2, "─" * (width - 4))
            stdscr.addstr(height - 1, (width - len(footer)) // 2, footer)
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.stats = {k: 0 for k in self.stats if k not in ['last_pair', 'last_trade', 'start_time']}
                self.events.clear()
                self.tokens_per_minute.clear()
            
            # Aktualisiere Daten
            self.read_logs()
            time.sleep(1)

def main():
    """Main entry point"""
    monitor = BotMonitor()
    
    # Initial load
    print("📊 Loading bot statistics...")
    monitor.read_logs()
    
    # Start dashboard
    try:
        curses.wrapper(monitor.draw_dashboard)
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
