#!/usr/bin/env python3
"""
Asus Screen Toggle User Agent
Sleduje stav klávesnice a spravuje ikonu v oznamovací oblasti.
"""

import sys
import os
import signal
import subprocess
import warnings
import gettext
import locale
import shutil
from pydbus.generic import signal as Signal

# --- Globální nastavení ---
DEBUG = False  # Pro vývoj nastavte na True

def debug_log(message):
    """Tiskne ladicí zprávy pouze pokud je aktivní DEBUG režim."""
    if DEBUG:
        print(f"DEBUG: {message}")

# --- Lokalizace ---
APP_NAME = "asus-screen-toggle"
LOCALE_DIR = "/usr/share/locale"

try:
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    _ = gettext.gettext
except Exception as e:
    debug_log(f"Localization failed to load: {e}")
    _ = lambda s: s

warnings.filterwarnings("ignore")

# --- Importy GUI knihoven ---
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
    from pydbus import SessionBus

    # Detekce AppIndicatoru (Ayatana vs Standard)
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
    except (ValueError, ImportError):
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
except Exception as e:
    sys.stderr.write(f"FATAL: Required libraries missing: {e}\n")
    sys.exit(1)

# --- Konfigurace cest ---
BUS_NAME = "org.asus.ScreenToggle"
SCRIPT_NAME = "asus-check-keyboard-user"
SETTINGS_NAME = "asus-screen-settings"

# Dynamické nalezení cest k binárkám
SCRIPT_PATH = shutil.which(SCRIPT_NAME) or f"/usr/bin/{SCRIPT_NAME}"
SETTINGS_PATH = shutil.which(SETTINGS_NAME) or f"/usr/bin/{SETTINGS_NAME}"

ICON_PATH = "/usr/share/asus-screen-toggle"
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")
SYS_CONFIG = "/etc/asus-screen-toggle.conf"
USER_CONFIG = os.path.expanduser("~/.config/asus-screen-toggle/user.conf")

# Ikony
ICON_AUTO_NAME = "icon-green"
ICON_PRIMARY_NAME = "icon-red"
ICON_DESKTOP_NAME = "icon-blue"

class StatusNotifierItem:
    """Implementace org.kde.StatusNotifierItem pro lepší integraci s KDE Plasma."""

    <node>
      <interface name="org.kde.StatusNotifierItem">
        <property name="Category" type="s" access="read"/>
        <property name="Id" type="s" access="read"/>
        <property name="Title" type="s" access="read"/>
        <property name="Status" type="s" access="read"/>
        <property name="IconName" type="s" access="read"/>
        <property name="IconThemePath" type="s" access="read"/>
        <property name="ItemIsMenu" type="b" access="read"/>
        <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
        <method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
        <method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
        <method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
        <signal name="NewIcon"/><signal name="NewStatus"/><signal name="NewToolTip"/>
      </interface>
    </node>

    NewIcon = Signal()
    NewStatus = Signal()
    NewToolTip = Signal()

    def __init__(self, agent):
        self.agent = agent
        self.icon_name = ICON_AUTO_NAME
        self.status = "Active"

    @property
    def Category(self): return "Hardware"
    @property
    def Id(self): return "asus-screen-toggle"
    @property
    def Title(self): return _("Asus Screen Toggle")
    @property
    def Status(self): return self.status
    @property
    def IconName(self): return self.icon_name
    @property
    def IconThemePath(self): return ICON_PATH
    @property
    def ItemIsMenu(self): return False
    @property
    def ToolTip(self): return (self.icon_name, [], _("Asus Screen Toggle"), _(f"Režim: {self.agent.mode}"))

    def Activate(self, x, y):
        GLib.idle_add(self.agent._launch_settings)

    def ContextMenu(self, x, y):
        GLib.idle_add(self.agent._show_gtk_menu)

    def SecondaryActivate(self, x, y):
        self.agent._run_check("Tray_MiddleClick")

    def set_icon(self, name):
        if self.icon_name != name:
            self.icon_name = name
            self.NewIcon()
            self.NewToolTip()

class AsusAgent:
    # Hlavní logika agenta, správa D-Bus a stavu aplikace."""
    """
    <node>
      <interface name="org.asus.ScreenToggle">
        <method name="Trigger"/>
        <method name="SetMode">
          <arg type="s" name="mode" direction="in"/>
        </method>
        <method name="ReloadConfig"/>
        <method name="Quit"/>
      </interface>
    </node>
    """

    def __init__(self, quit_callback, bus):
        self.quit_callback = quit_callback
        self.bus = bus
        self.mode = self._load_mode()
        self.config = self._load_config()
        self.indicator = None
        self.tray_backend = None

        self.last_file_mtime = 0
        if os.path.exists(STATE_FILE):
            self.last_file_mtime = os.stat(STATE_FILE).st_mtime

        # Inicializace Tray podle prostředí
        if os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "kde":
            try:
                self._setup_sni()
            except Exception as e:
                debug_log(f"SNI failed, using AppIndicator: {e}")
                self._setup_appindicator()
        else:
            self._setup_appindicator()

        GLib.timeout_add_seconds(2, self._monitor_file_change)

    def _load_config(self):
        """Načte konfiguraci s logikou AND (Systém & Uživatel)."""
        cfg = {"enable_dbus": True, "enable_signal": True}
        paths = [SYS_CONFIG, USER_CONFIG]

        for path in paths:
            if os.path.exists(path):
                try:
                    debug_log(f"Reading config: {path}")
                    with open(path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if "=" in line and not line.startswith("#"):
                                key, val = line.split("=", 1)
                                key = key.strip().upper()
                                is_true = (val.strip().lower() == "true")
                                if key in ["ENABLE_DBUS", "ENABLE_SIGNAL"]:
                                    cfg[key.lower()] = is_true and cfg[key.lower()]
                except: pass
        return cfg

    def _monitor_file_change(self):
        """Sleduje externí změny stavového souboru."""
        if os.path.exists(STATE_FILE):
            try:
                mtime = os.stat(STATE_FILE).st_mtime
                if mtime != self.last_file_mtime:
                    self.last_file_mtime = mtime
                    new_mode = self._load_mode()
                    if new_mode != self.mode:
                        debug_log(f"External state change: {new_mode}")
                        self.mode = new_mode
                        self._set_icon_by_mode()
            except: pass
        return True

    def _load_mode(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
                        return mode
            except: pass
        return "automatic-enabled"

    def _run_check(self, source="Internal"):
        debug_log(f"Running check logic (Source: {source})")
        try:
            subprocess.Popen([SCRIPT_PATH])
        except Exception as e:
            sys.stderr.write(f"Error executing {SCRIPT_PATH}: {e}\n")

    def _set_icon_by_mode(self):
        names = {
            "automatic-enabled": ICON_AUTO_NAME,
            "enforce-primary-only": ICON_PRIMARY_NAME,
            "enforce-desktop": ICON_DESKTOP_NAME
        }
        icon = names.get(self.mode, ICON_AUTO_NAME)

        if self.tray_backend == "sni":
            self.sni.set_icon(icon)
        elif self.indicator:
            full_path = os.path.join(ICON_PATH, f"{icon}.svg")
            self.indicator.set_icon_full(full_path, icon)

    def _launch_settings(self):
        try:
            subprocess.Popen([SETTINGS_PATH])
        except: pass
        return False

    def _build_menu(self):
        menu = Gtk.Menu()

        title = Gtk.MenuItem(label=_("Asus Screen Control"))
        title.set_sensitive(False)
        menu.append(title)
        menu.append(Gtk.SeparatorMenuItem())

        r_auto = Gtk.RadioMenuItem(label=_("🤖 Automaticky"))
        r_auto.connect("toggled", self._on_mode_change, "automatic-enabled")
        menu.append(r_auto)

        group = r_auto.get_group()
        r_prim = Gtk.RadioMenuItem(label=_("💻 Jen hlavní displej"), group=group)
        r_prim.connect("toggled", self._on_mode_change, "enforce-primary-only")
        menu.append(r_prim)

        r_both = Gtk.RadioMenuItem(label=_("🖥️🖥️ Oba displeje"), group=group)
        r_both.connect("toggled", self._on_mode_change, "enforce-desktop")
        menu.append(r_both)

        # Nastavení aktivní položky
        if self.mode == "enforce-primary-only": r_prim.set_active(True)
        elif self.mode == "enforce-desktop": r_both.set_active(True)
        else: r_auto.set_active(True)

        menu.append(Gtk.SeparatorMenuItem())

        item_sets = Gtk.MenuItem(label=_("⚙️ Nastavení"))
        item_sets.connect("activate", lambda _: self._launch_settings())
        menu.append(item_sets)

        item_quit = Gtk.MenuItem(label=_("Ukončit"))
        item_quit.connect("activate", lambda _: self.Quit())
        menu.append(item_quit)

        menu.show_all()
        return menu

    def _on_mode_change(self, widget, mode_name):
        if widget.get_active() and self.mode != mode_name:
            self.mode = mode_name
            try:
                os.makedirs(STATE_DIR, exist_ok=True)
                with open(STATE_FILE, 'w') as f: f.write(mode_name)
            except: pass
            self._set_icon_by_mode()
            self._run_check("MenuChange")

    def _setup_appindicator(self):
        self.indicator = AppIndicator.Indicator.new(
            "asus-screen-toggler", ICON_AUTO_NAME,
            AppIndicator.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.set_icon_theme_path(ICON_PATH)
        self.indicator.set_menu(self._build_menu())
        self.tray_backend = "appindicator"
        self._set_icon_by_mode()

    def _setup_sni(self):
        self.sni = StatusNotifierItem(self)
        self.bus.register_object("/StatusNotifierItem", self.sni, None)
        self.tray_backend = "sni"
        self._set_icon_by_mode()

        try:
            watcher = self.bus.get("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher")
            watcher.RegisterStatusNotifierItem(BUS_NAME)
        except: pass

    def _show_gtk_menu(self):
        menu = self._build_menu()
        menu.popup_at_pointer(None)

    # --- D-Bus API ---
    def SetMode(self, mode):
        if mode in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
            self.mode = mode
            self._on_mode_change(Gtk.MenuItem(), mode) # Simulace aktivace
            return "OK"
        return "INVALID_MODE"

    def Quit(self):
        self.quit_callback()

def signal_handler(signum, frame):
    if not agent.config["enable_signal"]:
        return
    if agent.mode == "automatic-enabled":
        agent._run_check("SIGUSR1")

if __name__ == "__main__":
    bus = SessionBus()

    # Singleton kontrola
    dbus_proxy = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
    if dbus_proxy.NameHasOwner(BUS_NAME):
        sys.exit(0)

    agent = AsusAgent(quit_callback=lambda: Gtk.main_quit(), bus=bus)

    try:
        bus.publish(BUS_NAME, agent)
    except Exception as e:
        sys.stderr.write(f"D-Bus publication failed: {e}\n")
        sys.exit(1)

    # Signály
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1,
                         lambda: (signal_handler(None, None), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGHUP,
                         lambda: (setattr(agent, 'config', agent._load_config()), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)

    debug_log(f"Asus Agent started (PID: {os.getpid()})")
    Gtk.main()
