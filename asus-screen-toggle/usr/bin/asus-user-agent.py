#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import warnings

# Potlačení warningů
warnings.filterwarnings("ignore")

from pydbus.generic import signal as Signal

# --- Importy knihoven ---
print("DEBUG: Načítám knihovny...")
try:
    import gi
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
    except (ValueError, ImportError):
        try:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3 as AppIndicator
        except (ValueError, ImportError):
            print("CHYBA: Nenalezena knihovna AppIndicator.")
            sys.exit(1)

    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
    from pydbus import SessionBus
except Exception as e:
    print(f"CHYBA při importu knihoven: {e}")
    sys.exit(1)

# --- Konfigurace ---
BUS_NAME = "org.asus.ScreenToggle"
SCRIPT_PATH = "/usr/bin/asus-check-keyboard-user.sh"
APP_ID = "asus-screen-toggler"
ICON_NAME = "input-tablet"
ICON_PATH = "/usr/share/asus-screen-toggle"

ICON_AUTO_NAME = "icon-green.svg"
ICON_PRIMARY_NAME = "icon-red.svg"
ICON_DESKTOP_NAME = "icon-blue.svg"
ICON_AUTO = os.path.join(ICON_PATH, ICON_AUTO_NAME)
ICON_PRIMARY = os.path.join(ICON_PATH, ICON_PRIMARY_NAME)
ICON_DESKTOP = os.path.join(ICON_PATH, ICON_DESKTOP_NAME)

STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")
CONFIG_FILE = os.path.expanduser("~/.config/asus-screen-toggle/config.conf") # <--- NOVÉ

class StatusNotifierItem:
    """
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

        <method name="Activate">
          <arg type="i" direction="in"/>
          <arg type="i" direction="in"/>
        </method>

        <method name="ContextMenu">
          <arg type="i" direction="in"/>
          <arg type="i" direction="in"/>
        </method>

        <method name="SecondaryActivate">
          <arg type="i" direction="in"/>
          <arg type="i" direction="in"/>
        </method>

        <signal name="NewIcon"/>
        <signal name="NewStatus"/>
        <signal name="NewToolTip"/>
      </interface>
    </node>
    """
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
    def Title(self): return "Asus Screen Toggle"
    @property
    def Status(self): return self.status
    @property
    def IconName(self): return self.icon_name
    @property
    def IconThemePath(self): return ICON_PATH
    @property
    def ItemIsMenu(self): return False
    @property
    def Menu(self): return "/StatusNotifierItem"
    @property
    def ToolTip(self):
        return (self.icon_name, [], "Asus Screen Toggle", f"Režim: {self.agent.mode}")

    def Activate(self, x, y):
        GLib.idle_add(self.agent._show_gtk_menu, 1)

    def ContextMenu(self, x, y):
        GLib.idle_add(self.agent._show_gtk_menu, 3)

    def SecondaryActivate(self, x, y):
        print("SNI: Middle Click -> Quick Check")
        self.agent._run_check("SNI_MiddleClick")

    def set_icon(self, name):
        base_name = os.path.splitext(os.path.basename(name))[0]
        if self.icon_name != base_name:
            self.icon_name = base_name
            self.NewIcon()
            self.NewToolTip()

    def set_status(self, status):
        self.status = status
        self.NewStatus()


class AsusAgent:
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
        self.mode = self._load_mode()
        self.config = self._load_config() # <--- NOVÉ: Načtení konfigurace
        self.bus = bus
        self.indicator = None
        self.tray_backend = None
        self.menu = None

        if is_kde():
            try:
                self._setup_sni()
            except Exception as e:
                print(f"SNI selhalo, fallback na AppIndicator: {e}")
                self._setup_appindicator()
                self.tray_backend = "appindicator"
        else:
            self._setup_appindicator()
            self.tray_backend = "appindicator"

    # --- Konfigurace ---
    def _load_config(self):
        """Načte konfiguraci ze souboru."""
        cfg = {"enable_dbus": True, "enable_signal": True}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, val = line.strip().split("=", 1)
                            key = key.strip().upper()
                            val = val.strip().lower() == "true"
                            if key == "ENABLE_DBUS": cfg["enable_dbus"] = val
                            if key == "ENABLE_SIGNAL": cfg["enable_signal"] = val
                print(f"⚙️ Konfigurace načtena: {cfg}")
            except Exception as e:
                print(f"⚠️ Chyba configu: {e}")
        return cfg

    def ReloadConfig(self):
        """D-Bus metoda pro znovunačtení konfigurace bez restartu."""
        self.config = self._load_config()
        return "Config Reloaded"

    # --- Práce se souborem ---
    def _load_mode(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
                        print(f"📂 Načten režim ze souboru: {mode}")
                        return mode
            except: pass
        return "automatic-enabled"

    def _save_mode(self, mode):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                f.write(mode)
            print(f"💾 Režim '{mode}' uložen do {STATE_FILE}")
        except Exception as e:
            print(f"❌ Chyba configu: {e}")

    # --- D-Bus Metody ---
    def Trigger(self):
        # <--- NOVÉ: Kontrola konfigurace
        if not self.config["enable_dbus"]:
            print("📨 D-Bus: Požadavek ZAMÍTNUT (vypnuto v configu).")
            return "DISABLED_BY_CONFIG"

        if self.mode != "automatic-enabled":
            print(f"📨 D-Bus: Ignorováno (Vynucen režim: {self.mode})")
            return f"IGNORED: Mode is {self.mode}"

        print("📨 D-Bus: Požadavek přijat (Auto).")
        self._run_check("D-Bus")
        return "OK"

    def SetMode(self, mode_str):
        if mode_str not in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
            return "ERROR: Invalid mode"
        self.mode = mode_str
        self._save_mode(mode_str)
        self._set_icon_by_mode()
        self._run_check("D-Bus_SetMode")
        return f"OK: Switched to {mode_str}"

    def Quit(self):
        print("🛑 Požadavek na ukončení...")
        self.quit_callback()

    # --- Interní logika ---
    def _run_check(self, source="Internal"):
        print(f"🚀 Spouštím logiku (Režim: {self.mode}, Zdroj: {source})...")
        try:
            subprocess.Popen([SCRIPT_PATH])
        except FileNotFoundError:
            print(f"❌ Chyba: Skript {SCRIPT_PATH} nebyl nalezen.")

    def _set_icon_by_mode(self):
        if self.tray_backend == "sni":
            if self.mode == "automatic-enabled": self.sni.set_icon(ICON_AUTO_NAME)
            elif self.mode == "enforce-primary-only": self.sni.set_icon(ICON_PRIMARY_NAME)
            else: self.sni.set_icon(ICON_DESKTOP_NAME)
        elif self.indicator:
            icon_to_set = ICON_NAME
            if self.mode == "automatic-enabled":
                if os.path.exists(ICON_AUTO): icon_to_set = ICON_AUTO
                self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            elif self.mode == "enforce-primary-only":
                if os.path.exists(ICON_PRIMARY): icon_to_set = ICON_PRIMARY
                self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            else:
                if os.path.exists(ICON_DESKTOP): icon_to_set = ICON_DESKTOP
                self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            try: self.indicator.set_icon(icon_to_set)
            except: self.indicator.set_icon(ICON_NAME)

    def _on_mode_change(self, widget, mode_name):
        if widget.get_active():
            self.mode = mode_name
            self._save_mode(mode_name)
            self._set_icon_by_mode()
            self._run_check("MenuChange")

    def _build_menu(self):
        menu = Gtk.Menu()

        item = Gtk.MenuItem(label="Asus Screen Control")
        item.set_sensitive(False)
        menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())

        r_auto = Gtk.RadioMenuItem(label="🤖 Automaticky (Senzory)")
        r_auto.connect("toggled", self._on_mode_change, "automatic-enabled")
        menu.append(r_auto)

        group = r_auto.get_group()
        r_prim = Gtk.RadioMenuItem(label="💻 Jen hlavní displej", group=group[0])
        r_prim.connect("toggled", self._on_mode_change, "enforce-primary-only")
        menu.append(r_prim)

        r_both = Gtk.RadioMenuItem(label="🖥️🖥️ Oba displeje", group=group[0])
        r_both.connect("toggled", self._on_mode_change, "enforce-desktop")
        menu.append(r_both)

        if self.mode == "automatic-enabled": r_auto.set_active(True)
        elif self.mode == "enforce-primary-only": r_prim.set_active(True)
        elif self.mode == "enforce-desktop": r_both.set_active(True)

        menu.append(Gtk.SeparatorMenuItem())

        item_check = Gtk.MenuItem(label="Zkontrolovat")
        item_check.connect("activate", lambda _: self._run_check())
        menu.append(item_check)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Ukončit")
        item_quit.connect("activate", lambda _: self.Quit())
        menu.append(item_quit)

        menu.show_all()
        return menu

    def _setup_appindicator(self):
        self.indicator = AppIndicator.Indicator.new(
            APP_ID, ICON_NAME, AppIndicator.IndicatorCategory.HARDWARE
        )
        self._set_icon_by_mode()
        self.indicator.set_menu(self._build_menu())

    def _setup_sni(self):
        print("🔵 Inicializuji KDE StatusNotifierItem (SNI)")
        self.sni = StatusNotifierItem(self)
        try:
            self.bus.register_object("/StatusNotifierItem", self.sni, None)
            self.tray_backend = "sni"
            self._set_icon_by_mode()
            print("✅ SNI objekt vytvořen.")
        except Exception as e:
            print(f"❌ Chyba SNI: {e}")
            raise e

    def register_sni_watcher(self):
        if self.tray_backend == "sni":
            try:
                watcher = self.bus.get("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher")
                watcher.RegisterStatusNotifierItem(BUS_NAME)
                print("✅ SNI registrováno u KDE Watchera.")
                self.sni.NewIcon()
                self.sni.NewStatus()
            except Exception as e:
                print(f"⚠️ Watcher error: {e}")

    def _show_gtk_menu(self, button):
        try:
            self.menu = self._build_menu()
            self.menu.show_all()
            self.menu.popup(None, None, None, None, 0, 0)
        except Exception as e:
            print(f"❌ Chyba při zobrazování menu: {e}")
        return False


def is_kde():
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "kde"

# --- Main Boilerplate ---
loop = None
publication = None

def quit_app(*args):
    global publication, loop
    print("\n🧹 Ukončuji...")
    if publication:
        try: publication.unpublish()
        except: pass
    if loop: Gtk.main_quit()
    sys.exit(0)

def signal_handler():
    # <--- NOVÉ: Kontrola konfigurace pro signály (včetně systémového skriptu)
    if not agent.config["enable_signal"]:
        print("📩 Signál SIGUSR1 ZAMÍTNUT (vypnuto v configu).")
        return True

    if agent.mode == "automatic-enabled":
        print("📩 Signál SIGUSR1 přijat!")
        agent._run_check("Signal")
    else:
        print(f"📩 Signál SIGUSR1 ignorován (Režim ze souboru: {agent.mode}).")
    return True

if __name__ == "__main__":
    bus = SessionBus()

    dbus_sys = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
    if dbus_sys.NameHasOwner(BUS_NAME):
        print(f"⚠️ Agent už běží.")
        sys.exit(0)

    agent = AsusAgent(quit_callback=quit_app, bus=bus)

    try:
        publication = bus.publish(BUS_NAME, agent)
        print(f"✅ D-Bus jméno {BUS_NAME} získáno.")
        agent.register_sni_watcher()
    except Exception as e:
        print(f"❌ Start selhal: {e}")
        sys.exit(1)

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, signal_handler)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_app)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_app)

    print(f"✅ Asus Agent GUI spuštěn.")
    print(f"   Režim: {agent.mode}")
    print(f"   PID: {os.getpid()}")

    # Hlavní smyčka v bloku try/finally pro jistotu
    try:
        loop = Gtk.main()
    except KeyboardInterrupt:
        quit_app()
    finally:
        # Záchranná brzda, kdyby Gtk.main() spadlo jinak
        pass
