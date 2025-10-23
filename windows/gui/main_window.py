"""
Solana Memecoin Trading Bot - Windows Desktop Application
Professional GUI with real-time synchronization
"""
import sys
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QSystemTrayIcon, QMenu,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import bot core
try:
    from integration import integration_manager
    from trader import trader
    from scanner import scanner
    from config import scanner_filters, trading_config
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False


class ModernTheme:
    """Modern dark theme colors"""
    BACKGROUND = "#1e1e1e"
    SURFACE = "#2d2d2d"
    PRIMARY = "#0078d4"
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    BORDER = "#3d3d3d"


class SyncWorker(QThread):
    """Worker thread for bot operations"""
    status_update = pyqtSignal(dict)
    position_update = pyqtSignal(list)
    alert_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False

    def run(self):
        """Main worker loop"""
        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.running:
            try:
                # Get bot status
                if CORE_AVAILABLE:
                    status = {
                        'scanner_running': scanner.running if hasattr(scanner, 'running') else False,
                        'positions_count': len(trader.positions) if hasattr(trader, 'positions') else 0,
                        'total_pnl': trader.total_pnl if hasattr(trader, 'total_pnl') else 0,
                        'win_rate': trader.win_rate if hasattr(trader, 'win_rate') else 0
                    }
                    self.status_update.emit(status)

                    # Get positions
                    if hasattr(trader, 'positions'):
                        positions = []
                        for addr, pos in trader.positions.items():
                            positions.append({
                                'symbol': pos.symbol,
                                'address': addr,
                                'entry_price': pos.entry_price,
                                'current_price': pos.current_price,
                                'amount_sol': pos.amount_sol,
                                'pnl_pct': ((pos.current_price - pos.entry_price) / pos.entry_price) * 100
                            })
                        self.position_update.emit(positions)

                self.msleep(1000)  # Update every second

            except Exception as e:
                print(f"Worker error: {e}")
                self.msleep(5000)

    def stop(self):
        """Stop worker"""
        self.running = False


class DashboardWidget(QWidget):
    """Main dashboard with real-time metrics"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("📊 Real-Time Dashboard")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ModernTheme.TEXT_PRIMARY};")
        layout.addWidget(title)

        # Metrics Row
        metrics_layout = QHBoxLayout()

        # Bot Status Card
        self.bot_status = self.create_metric_card(
            "Bot Status",
            "🔴 Offline",
            ModernTheme.DANGER
        )
        metrics_layout.addWidget(self.bot_status)

        # Positions Card
        self.positions_card = self.create_metric_card(
            "Active Positions",
            "0",
            ModernTheme.PRIMARY
        )
        metrics_layout.addWidget(self.positions_card)

        # P&L Card
        self.pnl_card = self.create_metric_card(
            "Total P&L",
            "+0.0000 SOL",
            ModernTheme.SUCCESS
        )
        metrics_layout.addWidget(self.pnl_card)

        # Win Rate Card
        self.winrate_card = self.create_metric_card(
            "Win Rate",
            "0.0%",
            ModernTheme.WARNING
        )
        metrics_layout.addWidget(self.winrate_card)

        layout.addLayout(metrics_layout)

        # Positions Table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(6)
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Entry Price", "Current Price", "Amount (SOL)", "P&L %", "Actions"
        ])
        self.positions_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ModernTheme.SURFACE};
                color: {ModernTheme.TEXT_PRIMARY};
                border: 1px solid {ModernTheme.BORDER};
                border-radius: 8px;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {ModernTheme.BACKGROUND};
                color: {ModernTheme.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.positions_table)

        self.setStyleSheet(f"background-color: {ModernTheme.BACKGROUND};")

    def create_metric_card(self, title, value, color):
        """Create a metric display card"""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {ModernTheme.SURFACE};
                border: 1px solid {ModernTheme.BORDER};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout()

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10))
        title_label.setStyleSheet(f"color: {ModernTheme.TEXT_SECONDARY};")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setObjectName("value")
        layout.addWidget(value_label)

        card.setLayout(layout)
        return card

    def update_status(self, status):
        """Update dashboard with new status"""
        # Update bot status
        status_label = self.bot_status.findChild(QLabel, "value")
        if status['scanner_running']:
            status_label.setText("🟢 Online")
            status_label.setStyleSheet(f"color: {ModernTheme.SUCCESS};")
        else:
            status_label.setText("🔴 Offline")
            status_label.setStyleSheet(f"color: {ModernTheme.DANGER};")

        # Update positions count
        pos_label = self.positions_card.findChild(QLabel, "value")
        pos_label.setText(str(status['positions_count']))

        # Update P&L
        pnl_label = self.pnl_card.findChild(QLabel, "value")
        pnl = status['total_pnl']
        pnl_label.setText(f"{pnl:+.4f} SOL")
        pnl_label.setStyleSheet(f"color: {ModernTheme.SUCCESS if pnl >= 0 else ModernTheme.DANGER};")

        # Update win rate
        wr_label = self.winrate_card.findChild(QLabel, "value")
        wr_label.setText(f"{status['win_rate']:.1f}%")

    def update_positions(self, positions):
        """Update positions table"""
        self.positions_table.setRowCount(len(positions))

        for i, pos in enumerate(positions):
            self.positions_table.setItem(i, 0, QTableWidgetItem(pos['symbol']))
            self.positions_table.setItem(i, 1, QTableWidgetItem(f"${pos['entry_price']:.8f}"))
            self.positions_table.setItem(i, 2, QTableWidgetItem(f"${pos['current_price']:.8f}"))
            self.positions_table.setItem(i, 3, QTableWidgetItem(f"{pos['amount_sol']:.4f}"))

            # P&L with color
            pnl_item = QTableWidgetItem(f"{pos['pnl_pct']:+.2f}%")
            if pos['pnl_pct'] >= 0:
                pnl_item.setForeground(QColor(ModernTheme.SUCCESS))
            else:
                pnl_item.setForeground(QColor(ModernTheme.DANGER))
            self.positions_table.setItem(i, 4, pnl_item)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ModernTheme.DANGER};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 15px;
                }}
                QPushButton:hover {{
                    background-color: #dc2626;
                }}
            """)
            self.positions_table.setCellWidget(i, 5, close_btn)


class SettingsWidget(QWidget):
    """Settings configuration panel"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("⚙️ Bot Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ModernTheme.TEXT_PRIMARY};")
        layout.addWidget(title)

        # Settings Groups
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Scanner Settings
        scanner_group = self.create_scanner_settings()
        splitter.addWidget(scanner_group)

        # Trading Settings
        trading_group = self.create_trading_settings()
        splitter.addWidget(trading_group)

        layout.addWidget(splitter)

        # Save Button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernTheme.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1084e0;
            }}
        """)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        self.setStyleSheet(f"background-color: {ModernTheme.BACKGROUND};")

    def create_scanner_settings(self):
        """Create scanner settings group"""
        group = QGroupBox("Scanner Filters")
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {ModernTheme.SURFACE};
                border: 1px solid {ModernTheme.BORDER};
                border-radius: 8px;
                padding: 15px;
                color: {ModernTheme.TEXT_PRIMARY};
                font-weight: bold;
            }}
        """)

        layout = QFormLayout()

        self.min_liquidity = QSpinBox()
        self.min_liquidity.setRange(0, 10000000)
        self.min_liquidity.setValue(5000)
        self.min_liquidity.setSuffix(" USD")
        layout.addRow("Min Liquidity:", self.min_liquidity)

        self.max_liquidity = QSpinBox()
        self.max_liquidity.setRange(0, 10000000)
        self.max_liquidity.setValue(500000)
        self.max_liquidity.setSuffix(" USD")
        layout.addRow("Max Liquidity:", self.max_liquidity)

        self.min_score = QSpinBox()
        self.min_score.setRange(0, 100)
        self.min_score.setValue(70)
        layout.addRow("Min Score:", self.min_score)

        group.setLayout(layout)
        return group

    def create_trading_settings(self):
        """Create trading settings group"""
        group = QGroupBox("Trading Parameters")
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {ModernTheme.SURFACE};
                border: 1px solid {ModernTheme.BORDER};
                border-radius: 8px;
                padding: 15px;
                color: {ModernTheme.TEXT_PRIMARY};
                font-weight: bold;
            }}
        """)

        layout = QFormLayout()

        self.auto_buy = QCheckBox("Enable Auto-Buy")
        layout.addRow(self.auto_buy)

        self.base_amount = QDoubleSpinBox()
        self.base_amount.setRange(0.01, 10.0)
        self.base_amount.setValue(0.05)
        self.base_amount.setDecimals(2)
        self.base_amount.setSuffix(" SOL")
        layout.addRow("Base Trade Amount:", self.base_amount)

        self.stop_loss = QSpinBox()
        self.stop_loss.setRange(1, 50)
        self.stop_loss.setValue(15)
        self.stop_loss.setSuffix("%")
        layout.addRow("Stop Loss:", self.stop_loss)

        group.setLayout(layout)
        return group

    def save_settings(self):
        """Save settings to config"""
        print("Saving settings...")
        # TODO: Implement actual saving


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
        self.start_worker()

    def init_ui(self):
        self.setWindowTitle("Solana Memecoin Trading Bot - Professional Edition")
        self.setMinimumSize(1200, 800)

        # Set dark theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {ModernTheme.BACKGROUND};
            }}
            QTabWidget::pane {{
                border: 1px solid {ModernTheme.BORDER};
                border-radius: 8px;
                background-color: {ModernTheme.SURFACE};
            }}
            QTabBar::tab {{
                background-color: {ModernTheme.SURFACE};
                color: {ModernTheme.TEXT_SECONDARY};
                padding: 10px 20px;
                border: none;
            }}
            QTabBar::tab:selected {{
                background-color: {ModernTheme.PRIMARY};
                color: white;
            }}
        """)

        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Tabs
        tabs = QTabWidget()

        # Dashboard Tab
        self.dashboard = DashboardWidget()
        tabs.addTab(self.dashboard, "📊 Dashboard")

        # Settings Tab
        self.settings = SettingsWidget()
        tabs.addTab(self.settings, "⚙️ Settings")

        # Logs Tab
        logs = QTextEdit()
        logs.setReadOnly(True)
        logs.setStyleSheet(f"""
            background-color: {ModernTheme.SURFACE};
            color: {ModernTheme.TEXT_PRIMARY};
            border: none;
        """)
        tabs.addTab(logs, "📜 Logs")

        layout.addWidget(tabs)

        # Status Bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet(f"""
            background-color: {ModernTheme.SURFACE};
            color: {ModernTheme.TEXT_SECONDARY};
        """)

        # System Tray
        self.create_tray_icon()

    def create_tray_icon(self):
        """Create system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        # self.tray_icon.setIcon(QIcon("windows/resources/icons/app.png"))

        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def start_worker(self):
        """Start background worker"""
        self.worker = SyncWorker()
        self.worker.status_update.connect(self.dashboard.update_status)
        self.worker.position_update.connect(self.dashboard.update_positions)
        self.worker.start()

    def closeEvent(self, event):
        """Handle close event"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
