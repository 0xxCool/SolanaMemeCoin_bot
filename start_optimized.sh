#!/bin/bash
# ==============================================================================
# Solana Memecoin Bot - ULTRA-OPTIMIERTES START SCRIPT v3.0
# ==============================================================================
# Features:
# - Auto-Restart bei Crashes
# - Performance Monitoring
# - Detailliertes Logging
# - Health Checks
# - Multi-Process Management
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
MAX_RESTARTS=5
RESTART_DELAY=10
LOG_DIR="logs"
PID_FILE=".bot.pid"
HEALTH_CHECK_INTERVAL=60

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

print_header() {
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}\n"
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

# ==============================================================================
# PRE-START CHECKS
# ==============================================================================

check_environment() {
    print_header "Umgebungs-Check"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 nicht gefunden!"
        exit 1
    fi
    print_success "Python3: $(python3 --version)"
    
    # Check Virtual Environment
    if [ ! -d "venv" ]; then
        print_error "Virtual Environment nicht gefunden!"
        print_info "Führe zuerst ./setup.sh aus"
        exit 1
    fi
    print_success "Virtual Environment: OK"
    
    # Check .env
    if [ ! -f ".env" ]; then
        print_error ".env Datei nicht gefunden!"
        print_info "Kopiere .env.example zu .env und konfiguriere"
        exit 1
    fi
    print_success ".env Datei: OK"
    
    # Validate critical env vars
    source .env
    local missing_vars=()
    
    if [ -z "$PRIVATE_KEY" ]; then missing_vars+=("PRIVATE_KEY"); fi
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then missing_vars+=("TELEGRAM_BOT_TOKEN"); fi
    if [ -z "$TELEGRAM_CHAT_ID" ]; then missing_vars+=("TELEGRAM_CHAT_ID"); fi
    if [ -z "$RPC_URL" ]; then missing_vars+=("RPC_URL"); fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Fehlende Environment Variables:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        exit 1
    fi
    print_success "Alle kritischen ENV Variablen gesetzt"
}

setup_logging() {
    print_header "Logging Setup"
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Rotate old logs
    if [ -f "$LOG_DIR/bot.log" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        mv "$LOG_DIR/bot.log" "$LOG_DIR/bot_${timestamp}.log"
        print_info "Alte Logs archiviert: bot_${timestamp}.log"
    fi
    
    # Clean old logs (keep last 10)
    local log_count=$(ls -1 "$LOG_DIR"/bot_*.log 2>/dev/null | wc -l)
    if [ "$log_count" -gt 10 ]; then
        print_info "Räume alte Logs auf..."
        ls -1t "$LOG_DIR"/bot_*.log | tail -n +11 | xargs rm -f
    fi
    
    print_success "Logging bereit: $LOG_DIR/bot.log"
}

check_ports() {
    print_header "Port-Check"
    
    # Check Health Check Port (8000)
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8000 bereits belegt (Health Check)"
        local pid=$(lsof -Pi :8000 -sTCP:LISTEN -t)
        print_info "PID: $pid"
        read -p "Soll der Prozess beendet werden? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill -9 "$pid"
            sleep 2
            print_success "Port 8000 freigegeben"
        else
            print_warning "Bot läuft möglicherweise bereits"
            exit 1
        fi
    else
        print_success "Port 8000 verfügbar"
    fi
}

# ==============================================================================
# MAIN BOT FUNCTIONS
# ==============================================================================

start_bot() {
    local restart_count=0
    
    print_header "Starte Bot"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Save PID
    echo $$ > "$PID_FILE"
    
    while [ $restart_count -lt $MAX_RESTARTS ]; do
        if [ $restart_count -gt 0 ]; then
            print_warning "Neustart #$restart_count/$MAX_RESTARTS in ${RESTART_DELAY}s..."
            sleep $RESTART_DELAY
        fi
        
        print_success "Bot wird gestartet..."
        print_info "Logs: tail -f $LOG_DIR/bot.log"
        print_info "Health Check: http://localhost:8000/health"
        echo ""
        
        # Start bot with enhanced logging
        python3 main.py 2>&1 | tee -a "$LOG_DIR/bot.log"
        
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            print_success "Bot sauber beendet"
            break
        else
            print_error "Bot crashed mit Exit Code: $exit_code"
            restart_count=$((restart_count + 1))
            
            # Log crash
            echo "[$(date)] Bot crashed with exit code $exit_code" >> "$LOG_DIR/crashes.log"
            
            # Check if max restarts reached
            if [ $restart_count -ge $MAX_RESTARTS ]; then
                print_error "Maximale Anzahl von Neustarts erreicht!"
                print_info "Prüfe die Logs: $LOG_DIR/bot.log"
                print_info "Crash-Log: $LOG_DIR/crashes.log"
                exit 1
            fi
        fi
    done
    
    # Cleanup
    rm -f "$PID_FILE"
}

stop_bot() {
    print_header "Stoppe Bot"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid"
            print_success "Bot gestoppt (PID: $pid)"
            rm -f "$PID_FILE"
        else
            print_warning "Bot läuft nicht (PID aus File: $pid)"
            rm -f "$PID_FILE"
        fi
    else
        # Try to find by process name
        local pids=$(pgrep -f "python3 main.py")
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -TERM
            print_success "Bot-Prozesse gestoppt"
        else
            print_info "Kein laufender Bot gefunden"
        fi
    fi
}

status_bot() {
    print_header "Bot Status"
    
    # Check PID file
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_success "Bot läuft (PID: $pid)"
            
            # Show resource usage
            local cpu=$(ps -p "$pid" -o %cpu --no-headers)
            local mem=$(ps -p "$pid" -o %mem --no-headers)
            local runtime=$(ps -p "$pid" -o etime --no-headers)
            
            echo ""
            echo "  CPU:     ${cpu}%"
            echo "  Memory:  ${mem}%"
            echo "  Runtime: ${runtime}"
            echo ""
            
            # Check Health Endpoint
            if command -v curl &> /dev/null; then
                print_info "Health Check..."
                curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || print_warning "Health endpoint nicht erreichbar"
            fi
            
            return 0
        else
            print_error "PID File existiert, aber Prozess läuft nicht"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        # Check by process name
        local pids=$(pgrep -f "python3 main.py")
        if [ -n "$pids" ]; then
            print_warning "Bot läuft, aber kein PID File"
            echo "PIDs: $pids"
            return 0
        else
            print_info "Bot läuft nicht"
            return 1
        fi
    fi
}

show_logs() {
    print_header "Live Logs"
    print_info "Drücke Ctrl+C zum Beenden"
    echo ""
    
    if [ -f "$LOG_DIR/bot.log" ]; then
        tail -f "$LOG_DIR/bot.log"
    else
        print_error "Keine Logs gefunden"
        exit 1
    fi
}

show_stats() {
    print_header "Bot Statistiken"
    
    if [ ! -f "$LOG_DIR/bot.log" ]; then
        print_error "Keine Logs gefunden"
        return
    fi
    
    echo "📊 Letzte 1000 Zeilen analysiert:"
    echo ""
    
    # Count key events
    local pairs_found=$(tail -1000 "$LOG_DIR/bot.log" | grep -c "Neues Pair gefunden" || echo 0)
    local passed_filter=$(tail -1000 "$LOG_DIR/bot.log" | grep -c "⚡ TRADE SIGNAL" || echo 0)
    local trades=$(tail -1000 "$LOG_DIR/bot.log" | grep -c "✅ Trade erfolgreich" || echo 0)
    local errors=$(tail -1000 "$LOG_DIR/bot.log" | grep -c "ERROR\|❌" || echo 0)
    local warnings=$(tail -1000 "$LOG_DIR/bot.log" | grep -c "WARNING\|⚠️" || echo 0)
    
    echo "  Pairs gefunden:    $pairs_found"
    echo "  Filter bestanden:  $passed_filter"
    echo "  Trades ausgeführt: $trades"
    echo "  Fehler:            $errors"
    echo "  Warnungen:         $warnings"
    echo ""
    
    # Show recent activity
    print_info "Letzte Aktivität:"
    tail -20 "$LOG_DIR/bot.log" | grep -E "Neues Pair|TRADE SIGNAL|Trade erfolgreich" || echo "  Keine relevanten Events"
}

# ==============================================================================
# OPTIMIZATION FUNCTIONS
# ==============================================================================

optimize_system() {
    print_header "System-Optimierung"
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Läuft als Root - System-Optimierungen verfügbar"
        
        # Increase file descriptor limits
        ulimit -n 65535 2>/dev/null && print_success "File descriptors erhöht: 65535" || print_warning "Konnte File descriptors nicht erhöhen"
        
        # Optimize network
        sysctl -w net.core.rmem_max=134217728 &>/dev/null && print_success "Network buffer optimiert" || true
        sysctl -w net.core.wmem_max=134217728 &>/dev/null || true
    else
        print_info "Nicht als Root - überspringe System-Optimierungen"
    fi
    
    # Python optimizations (PYTHONOPTIMIZE)
    export PYTHONOPTIMIZE=2
    print_success "Python Optimierungen aktiviert"
    
    # Set environment for better performance
    export PYTHONUNBUFFERED=1
    print_success "Python unbuffered IO aktiviert"
}

# ==============================================================================
# INTERACTIVE MENU
# ==============================================================================

show_menu() {
    clear
    print_header "Solana Memecoin Bot - Control Panel"
    
    echo "  1) Start Bot"
    echo "  2) Stop Bot"
    echo "  3) Restart Bot"
    echo "  4) Status anzeigen"
    echo "  5) Live Logs anzeigen"
    echo "  6) Statistiken anzeigen"
    echo "  7) System optimieren"
    echo "  8) Logs löschen"
    echo "  9) Health Check"
    echo "  0) Beenden"
    echo ""
    
    read -p "Wähle eine Option: " choice
    
    case $choice in
        1)
            check_environment
            setup_logging
            check_ports
            optimize_system
            start_bot
            ;;
        2)
            stop_bot
            ;;
        3)
            stop_bot
            sleep 2
            check_environment
            setup_logging
            start_bot
            ;;
        4)
            status_bot
            echo ""
            read -p "Drücke Enter zum Fortfahren..."
            show_menu
            ;;
        5)
            show_logs
            ;;
        6)
            show_stats
            echo ""
            read -p "Drücke Enter zum Fortfahren..."
            show_menu
            ;;
        7)
            optimize_system
            echo ""
            read -p "Drücke Enter zum Fortfahren..."
            show_menu
            ;;
        8)
            rm -rf "$LOG_DIR"/*.log
            print_success "Logs gelöscht"
            sleep 2
            show_menu
            ;;
        9)
            if command -v curl &> /dev/null; then
                curl -s http://localhost:8000/health | python3 -m json.tool
            else
                print_error "curl nicht installiert"
            fi
            echo ""
            read -p "Drücke Enter zum Fortfahren..."
            show_menu
            ;;
        0)
            print_success "Auf Wiedersehen!"
            exit 0
            ;;
        *)
            print_error "Ungültige Option"
            sleep 2
            show_menu
            ;;
    esac
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

# Handle command line arguments
if [ $# -eq 0 ]; then
    # No arguments - show interactive menu
    show_menu
else
    case "$1" in
        start)
            check_environment
            setup_logging
            check_ports
            optimize_system
            start_bot
            ;;
        stop)
            stop_bot
            ;;
        restart)
            stop_bot
            sleep 2
            check_environment
            setup_logging
            start_bot
            ;;
        status)
            status_bot
            ;;
        logs)
            show_logs
            ;;
        stats)
            show_stats
            ;;
        optimize)
            optimize_system
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs|stats|optimize}"
            echo "   or run without arguments for interactive menu"
            exit 1
            ;;
    esac
fi
