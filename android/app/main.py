"""
Solana Memecoin Trading Bot - Android Mobile App
Built with Kivy for cross-platform deployment
"""
import asyncio
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.uix.recycleview import RecycleView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
import websockets
import threading


class ModernColors:
    """Material Design color scheme"""
    PRIMARY = (0, 0.47, 0.83, 1)  # #0078d4
    SUCCESS = (0.06, 0.72, 0.51, 1)  # #10b981
    DANGER = (0.94, 0.27, 0.27, 1)  # #ef4444
    BACKGROUND = (0.12, 0.12, 0.12, 1)  # #1e1e1e
    SURFACE = (0.18, 0.18, 0.18, 1)  # #2d2d2d
    TEXT = (1, 1, 1, 1)  # white


class DashboardScreen(Screen):
    """Main dashboard screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        layout.canvas.before.clear()

        # Title
        title = Label(
            text="📊 Dashboard",
            font_size=dp(24),
            size_hint_y=None,
            height=dp(50),
            color=ModernColors.TEXT
        )
        layout.add_widget(title)

        # Metrics Grid
        metrics = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(200))

        # Status Card
        self.status_label = Label(
            text="Status\n🔴 Offline",
            halign='center',
            font_size=dp(16)
        )
        metrics.add_widget(self.create_card(self.status_label))

        # Positions Card
        self.positions_label = Label(
            text="Positions\n0",
            halign='center',
            font_size=dp(16)
        )
        metrics.add_widget(self.create_card(self.positions_label))

        # P&L Card
        self.pnl_label = Label(
            text="Total P&L\n+0.0000 SOL",
            halign='center',
            font_size=dp(16)
        )
        metrics.add_widget(self.create_card(self.pnl_label))

        # Win Rate Card
        self.winrate_label = Label(
            text="Win Rate\n0.0%",
            halign='center',
            font_size=dp(16)
        )
        metrics.add_widget(self.create_card(self.winrate_label))

        layout.add_widget(metrics)

        # Positions List
        positions_title = Label(
            text="Active Positions",
            font_size=dp(18),
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(positions_title)

        self.positions_list = RecycleView(size_hint_y=1)
        layout.add_widget(self.positions_list)

        self.add_widget(layout)

    def create_card(self, widget):
        """Create a card-style container"""
        card = BoxLayout(
            orientation='vertical',
            padding=dp(15)
        )
        card.add_widget(widget)
        return card

    def update_status(self, status):
        """Update dashboard with new data"""
        try:
            # Update status
            if status.get('scanner_running'):
                self.status_label.text = "Status\n🟢 Online"
            else:
                self.status_label.text = "Status\n🔴 Offline"

            # Update positions
            self.positions_label.text = f"Positions\n{status.get('positions_count', 0)}"

            # Update P&L
            pnl = status.get('total_pnl', 0)
            self.pnl_label.text = f"Total P&L\n{pnl:+.4f} SOL"

            # Update win rate
            wr = status.get('win_rate', 0)
            self.winrate_label.text = f"Win Rate\n{wr:.1f}%"

        except Exception as e:
            print(f"Update error: {e}")

    def update_positions(self, positions):
        """Update positions list"""
        try:
            data = []
            for pos in positions:
                pnl = pos.get('pnl_pct', 0)
                data.append({
                    'text': f"{pos['symbol']}\nP&L: {pnl:+.2f}%\nAmount: {pos['amount_sol']:.4f} SOL"
                })

            self.positions_list.data = data

        except Exception as e:
            print(f"Positions update error: {e}")


class SettingsScreen(Screen):
    """Settings configuration screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # Title
        title = Label(
            text="⚙️ Settings",
            font_size=dp(24),
            size_hint_y=None,
            height=dp(50)
        )
        layout.add_widget(title)

        # Scrollable settings
        scroll = ScrollView()
        settings_layout = GridLayout(
            cols=1,
            spacing=dp(10),
            size_hint_y=None,
            padding=dp(10)
        )
        settings_layout.bind(minimum_height=settings_layout.setter('height'))

        # Auto-Buy Toggle
        auto_buy_box = BoxLayout(size_hint_y=None, height=dp(50))
        auto_buy_box.add_widget(Label(text="Auto-Buy:", size_hint_x=0.7))
        self.auto_buy_switch = Switch(active=False)
        self.auto_buy_switch.bind(active=self.on_auto_buy_change)
        auto_buy_box.add_widget(self.auto_buy_switch)
        settings_layout.add_widget(auto_buy_box)

        # Auto-Sell Toggle
        auto_sell_box = BoxLayout(size_hint_y=None, height=dp(50))
        auto_sell_box.add_widget(Label(text="Auto-Sell:", size_hint_x=0.7))
        self.auto_sell_switch = Switch(active=False)
        self.auto_sell_switch.bind(active=self.on_auto_sell_change)
        auto_sell_box.add_widget(self.auto_sell_switch)
        settings_layout.add_widget(auto_sell_box)

        # Base Trade Amount
        amount_label = Label(
            text="Base Trade Amount: 0.05 SOL",
            size_hint_y=None,
            height=dp(30)
        )
        settings_layout.add_widget(amount_label)

        self.amount_slider = Slider(
            min=0.01,
            max=1.0,
            value=0.05,
            step=0.01,
            size_hint_y=None,
            height=dp(40)
        )
        self.amount_slider.bind(value=lambda i, v: setattr(amount_label, 'text', f"Base Trade Amount: {v:.2f} SOL"))
        settings_layout.add_widget(self.amount_slider)

        # Stop Loss
        sl_label = Label(
            text="Stop Loss: 15%",
            size_hint_y=None,
            height=dp(30)
        )
        settings_layout.add_widget(sl_label)

        self.sl_slider = Slider(
            min=5,
            max=50,
            value=15,
            step=1,
            size_hint_y=None,
            height=dp(40)
        )
        self.sl_slider.bind(value=lambda i, v: setattr(sl_label, 'text', f"Stop Loss: {int(v)}%"))
        settings_layout.add_widget(self.sl_slider)

        # Save Button
        save_btn = Button(
            text="💾 Save Settings",
            size_hint_y=None,
            height=dp(50),
            background_color=ModernColors.PRIMARY
        )
        save_btn.bind(on_press=self.save_settings)
        settings_layout.add_widget(save_btn)

        scroll.add_widget(settings_layout)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def on_auto_buy_change(self, instance, value):
        """Handle auto-buy toggle"""
        print(f"Auto-buy: {value}")

    def on_auto_sell_change(self, instance, value):
        """Handle auto-sell toggle"""
        print(f"Auto-sell: {value}")

    def save_settings(self, instance):
        """Save settings and sync"""
        settings = {
            'auto_buy_enabled': self.auto_buy_switch.active,
            'auto_sell_enabled': self.auto_sell_switch.active,
            'base_trade_amount_sol': self.amount_slider.value,
            'stop_loss': int(self.sl_slider.value)
        }

        # Send to API
        popup = Popup(
            title='Settings',
            content=Label(text='Settings saved successfully!'),
            size_hint=(None, None),
            size=(dp(300), dp(200))
        )
        popup.open()

        print(f"Saving settings: {settings}")


class SolanaTradingApp(App):
    """Main application class"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.websocket = None
        self.ws_thread = None
        self.running = False

    def build(self):
        """Build the application UI"""
        Window.clearcolor = ModernColors.BACKGROUND

        sm = ScreenManager()

        # Add screens
        self.dashboard = DashboardScreen(name='dashboard')
        sm.add_widget(self.dashboard)

        self.settings = SettingsScreen(name='settings')
        sm.add_widget(self.settings)

        # Navigation buttons
        nav_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(60),
            spacing=dp(5)
        )

        dash_btn = Button(
            text="📊 Dashboard",
            background_color=ModernColors.PRIMARY
        )
        dash_btn.bind(on_press=lambda x: setattr(sm, 'current', 'dashboard'))
        nav_layout.add_widget(dash_btn)

        settings_btn = Button(
            text="⚙️ Settings",
            background_color=ModernColors.PRIMARY
        )
        settings_btn.bind(on_press=lambda x: setattr(sm, 'current', 'settings'))
        nav_layout.add_widget(settings_btn)

        # Main layout
        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(sm)
        main_layout.add_widget(nav_layout)

        # Start WebSocket connection
        self.start_websocket()

        # Schedule status updates
        Clock.schedule_interval(self.request_status_update, 2.0)

        return main_layout

    def start_websocket(self):
        """Start WebSocket connection to sync server"""
        self.running = True
        self.ws_thread = threading.Thread(target=self.websocket_worker, daemon=True)
        self.ws_thread.start()

    def websocket_worker(self):
        """WebSocket connection worker"""
        asyncio.run(self.ws_loop())

    async def ws_loop(self):
        """Async WebSocket loop"""
        # Replace with your server URL
        uri = "ws://localhost:8765/ws/android"

        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket

                while self.running:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        # Handle different message types
                        if data.get('type') == 'status_update':
                            Clock.schedule_once(
                                lambda dt: self.dashboard.update_status(data.get('status', {})),
                                0
                            )
                            Clock.schedule_once(
                                lambda dt: self.dashboard.update_positions(data.get('positions', [])),
                                0
                            )

                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket connection closed")
                        break
                    except Exception as e:
                        print(f"WebSocket error: {e}")
                        await asyncio.sleep(5)

        except Exception as e:
            print(f"WebSocket connection error: {e}")

    def request_status_update(self, dt):
        """Request status update from server"""
        # This would send a request through WebSocket
        pass

    def on_stop(self):
        """Cleanup on app stop"""
        self.running = False
        if self.ws_thread:
            self.ws_thread.join(timeout=2)


if __name__ == '__main__':
    SolanaTradingApp().run()
