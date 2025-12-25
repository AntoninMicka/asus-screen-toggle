#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import warnings
import time # Nový import pro čas
import gettext
import locale

# Nastavení lokalizace
APP_NAME = "asus-screen-toggle"
LOCALE_DIR = "/usr/share/locale"

try:
    # Pokusíme se nastavit systémovou locale
    locale.setlocale(locale.LC_ALL, '')

    # Inicializace gettext
    gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    _ = gettext.gettext
except Exception as e:
    # Fallback, pokud gettext selže (např. při vývoji mimo instalaci)
    print(f"Warning: Localization not loaded: {e}")
    _ = lambda s: s

warnings.filterwarnings("ignore")
from pydbus.generic import signal as Signal

# --- Importy knihoven ---
print(_("DEBUG: Načítám knihovny..."))
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
            print(_("CHYBA: Nenalezena knihovna AppIndicator."))
            sys.exit(1)

    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
    from pydbus import SessionBus
except Exception as e:
    print(f_("CHYBA při importu knihoven: {e}"))
    sys.exit(1)

# --- Konfigurace ---
BUS_NAME = "org.asus.ScreenToggle"
SCRIPT_PATH = shutil.which("asus-check-keyboard-user") or "/usr/bin/asus-check-keyboard-user"
SETTINGS_PATH = shutil.which("asus-screen-settings") or "/usr/bin/asus-screen-settings"
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
CONFIG_FILE = os.path.expanduser("~/.config/asus-screen-toggle/config.conf")

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
    def Menu(self): return "/StatusNotifierItem"
    @property
    def ToolTip(self): return (self.icon_name, [], _("Asus Screen Toggle"), _(f"Režim: {self.agent.mode}"))

    def Activate(self, x, y):
        """Levý klik (SNI): Spustí přímo nastavení."""
        # Voláme pomocnou metodu agenta
        GLib.idle_add(self.agent._launch_settings)

    def ContextMenu(self, x, y):
        GLib.idle_add(self.agent._show_gtk_menu, 3)

    def SecondaryActivate(self, x, y):
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
        self.config = self._load_config()
        self.bus = bus
        self.indicator = None
        self.tray_backend = None
        self.menu = None

        # Pro sledování změn souboru
        self.last_file_mtime = 0
        if os.path.exists(STATE_FILE):
            self.last_file_mtime = os.stat(STATE_FILE).st_mtime

        if is_kde():
            try:
                self._setup_sni()
            except Exception as e:
                print(f_("SNI failed, fallback na AppIndicator: {e}"))
                self._setup_appindicator()
                self.tray_backend = "appindicator"
        else:
            self._setup_appindicator()
            self.tray_backend = "appindicator"

        # Timer pro sledování externích změn souboru (každé 2s)
        GLib.timeout_add_seconds(2, self._monitor_file_change)

    # --- Konfigurace ---
    def _load_config(self):
        """
        Načte konfiguraci s prioritou:
        1. Defaultní hodnoty (v kódu)
        2. Systémová konfigurace (/etc/asus-check-keyboard.cfg)
        3. Uživatelská konfigurace (~/.config/asus-screen-toggle/config.conf)
        """
        # 1. Defaultní hodnoty
        cfg = {"enable_dbus": True, "enable_signal": True}

        # Seznam souborů v pořadí, jak se mají aplikovat (poslední vyhrává)
        config_paths = [
            "/etc/asus-check-keyboard.cfg",
            os.path.expanduser("~/.config/asus-screen-toggle/config.conf")
        ]

        for path in config_paths:
            if os.path.exists(path):
                try:
                    print(_(f"⚙️ Načítám soubor: {path}"))
                    with open(path, 'r') as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, val = line.strip().split("=", 1)
                                key = key.strip().upper()
                                is_true = (val.strip().lower() == "true")

                                if key == "ENABLE_DBUS": cfg["enable_dbus"] = is_true and cfg["enable_dbus"]
                                elif key == "ENABLE_SIGNAL": cfg["enable_signal"] = (is_true and cfg["enable_signal"]
                except Exception as e:
                    print(f"Chyba při čtení {path}: {e}")

        print(_(f"Finální stav agenta: DBUS={cfg['enable_dbus']}, SIGNAL={cfg['enable_signal']}"))
        return cfg

    def _monitor_file_change(self):
        """Kontroluje, zda se soubor nezměnil externě (např. přes GUI Settings)."""
        if os.path.exists(STATE_FILE):
            try:
                mtime = os.stat(STATE_FILE).st_mtime
                if mtime != self.last_file_mtime:
                    # Soubor se změnil!
                    self.last_file_mtime = mtime
                    new_mode = self._load_mode(silent=True)
                    if new_mode != self.mode:
                        print(_(f"🔄 Detekována externí změna stavu -> {new_mode}"))
                        self.mode = new_mode
                        self._set_icon_by_mode()
                        # Zde nespouštíme _run_check, protože předpokládáme,
                        # že ten kdo soubor změnil (Settings App), už skript spustil nebo spustí.
                        # Jen aktualizujeme ikonu.
            except: pass
        return True # Pokračovat v timeru

    def _load_mode(self, silent=False):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
                        print(_(f"📂 Načten režim ze souboru: {mode}"))
                        return mode
            except: pass
        return "automatic-enabled"

    def _save_mode(self, mode):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                f.write(mode)
            print(_(f"💾 Režim '{mode}' uložen do {STATE_FILE}"))
        except Exception as e:
            print(_(f"❌ Chyba configu: {e}"))

    # --- D-Bus Metody ---
    def Trigger(self):
        if not self.config["enable_dbus"]: return "DISABLED_BY_CONFIG"
        if self.mode != "automatic-enabled": return f"IGNORED: Mode is {self.mode}"
        self._run_check("D-Bus")
        return "OK"

    def SetMode(self, mode_str):
        if mode_str not in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]: return "ERROR"
        print(_(f"📨 D-Bus SetMode: {mode_str}"))
        self.mode = mode_str
        self._save_mode(mode_str)
        self._set_icon_by_mode()
        self._run_check("D-Bus_SetMode")
        return _(f"OK: Switched to {mode_str}")

    def Quit(self):
        print("🛑 Požadavek na ukončení...")
        self.quit_callback()

    def _launch_settings(self):
        try: subprocess.Popen([SETTINGS_PATH])
        except: pass
        return False

    def _run_check(self, source="Internal"):
        print(_(f"🚀 Spouštím logiku ({source})..."))
        try: subprocess.Popen([SCRIPT_PATH])
        except: pass

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

        item = Gtk.MenuItem(label=_("Asus Screen Control"))
        item.set_sensitive(False)
        menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())

        r_auto = Gtk.RadioMenuItem(label=_("🤖 Automaticky"))
        r_auto.connect("toggled", self._on_mode_change, "automatic-enabled")
        menu.append(r_auto)

        group = r_auto.get_group()
        r_prim = Gtk.RadioMenuItem(label=_("💻 Jen hlavní displej"), group=group[0])
        r_prim.connect("toggled", self._on_mode_change, "enforce-primary-only")
        menu.append(r_prim)

        r_both = Gtk.RadioMenuItem(label=_("🖥️🖥️ Oba displeje"), group=group[0])
        r_both.connect("toggled", self._on_mode_change, "enforce-desktop")
        menu.append(r_both)

        if self.mode == "automatic-enabled": r_auto.set_active(True)
        elif self.mode == "enforce-primary-only": r_prim.set_active(True)
        elif self.mode == "enforce-desktop": r_both.set_active(True)

        menu.append(Gtk.SeparatorMenuItem())
        item_sets = Gtk.MenuItem(label=_("⚙️ Nastavení"))
        item_sets.connect("activate", lambda _: self._launch_settings())
        menu.append(item_sets)

        item_check = Gtk.MenuItem(label=_("Zkontrolovat"))
        item_check.connect("activate", lambda _: self._run_check())
        menu.append(item_check)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label=_("Ukončit"))
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
        print(_("🔵 Inicializuji KDE StatusNotifierItem (SNI)"))
        self.sni = StatusNotifierItem(self)
        try:
            self.bus.register_object("/StatusNotifierItem", self.sni, None)
            self.tray_backend = "sni"
            self._set_icon_by_mode()
            print(_("✅ SNI objekt vytvořen."))
        except Exception as e:
            print(_(f"❌ Chyba SNI: {e}"))
            raise e

    def register_sni_watcher(self):
        if self.tray_backend == "sni":
            try:
                watcher = self.bus.get("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher")
                watcher.RegisterStatusNotifierItem(BUS_NAME)
                print(_("✅ SNI registrováno u KDE Watchera."))
                self.sni.NewIcon()
                self.sni.NewStatus()
            except Exception as e:
                print(_(f"⚠️ Watcher error: {e}"))

    def _show_gtk_menu(self, button):
        try:
            self.menu = self._build_menu()
            self.menu.show_all()
            self.menu.popup(None, None, None, None, 0, 0)
        except Exception as e:
            print(_(f"❌ Chyba při zobrazování menu: {e}"))
        return False


def is_kde():
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "kde"

# --- Main Boilerplate ---
loop = None
publication = None

def quit_app(*args):
    global publication, loop
    print(_("\n🧹 Ukončuji..."))
    if publication:
        try: publication.unpublish()
        except: pass
    if loop: Gtk.main_quit()
    sys.exit(0)

def signal_handler():
    # <--- NOVÉ: Kontrola konfigurace pro signály (včetně systémového skriptu)
    if not agent.config["enable_signal"]:
        print(_("📩 Signál SIGUSR1 ZAMÍTNUT (vypnuto v configu)."))
        return True

    if agent.mode == "automatic-enabled":
        print(_("📩 Signál SIGUSR1 přijat!"))
        agent._run_check("Signal")
    else:
        print(_(f"📩 Signál SIGUSR1 ignorován (Režim ze souboru: {agent.mode})."))
    return True

def sighup_handler():
    """Obsluha signálu SIGHUP - Reload konfigurace."""
    print(_("🔄 Signál SIGHUP přijat: Znovunačítám konfiguraci..."))
    # Zavoláme metodu agenta, která načte soubory znovu
    agent.config = agent._load_config()
    return True # Musí vracet True, aby naslouchání pokračovalo

if __name__ == "__main__":
    bus = SessionBus()

    dbus_sys = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
    if dbus_sys.NameHasOwner(BUS_NAME):
        print(_(f"⚠️ Agent už běží."))
        sys.exit(0)

    agent = AsusAgent(quit_callback=quit_app, bus=bus)

    try:
        publication = bus.publish(BUS_NAME, agent)
        print(_(f"✅ D-Bus jméno {BUS_NAME} získáno."))
        agent.register_sni_watcher()
    except Exception as e:
        print(_(f"❌ Start selhal: {e}"))
        sys.exit(1)

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, signal_handler)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGHUP, sighup_handler)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_app)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_app)

    print(_(f"✅ Asus Agent GUI spuštěn."))
    print(_(f"   Režim: {agent.mode}"))
    print(_(f"   PID: {os.getpid()}"))

    # Hlavní smyčka v bloku try/finally pro jistotu
    try:
        loop = Gtk.main()
    except KeyboardInterrupt:
        quit_app()
    finally:
        # Záchranná brzda, kdyby Gtk.main() spadlo jinak
        pass
