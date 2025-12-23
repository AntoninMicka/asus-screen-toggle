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
ICON_NAME = "input-tablet" # Výchozí systémová ikona (backup)
ICON_PATH = "/usr/share/asus-screen-toggle"

# Ikony (ujistěte se, že existují, jinak yad nezobrazí nic)
# Pokud používáte absolutní cesty, AppIndicator je obvykle zvládne
ICON_AUTO_NAME = "icon-green.svg"
ICON_PRIMARY_NAME = "icon-red.svg"
ICON_DESKTOP_NAME = "icon-blue.svg"
ICON_AUTO = os.path.join(ICON_PATH, ICON_AUTO_NAME)
ICON_PRIMARY = os.path.join(ICON_PATH, ICON_PRIMARY_NAME)
ICON_DESKTOP = os.path.join(ICON_PATH, ICON_DESKTOP_NAME)

# Cesta k souboru s nastavením
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")

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
    # ... (Signály a __init__ zůstávají stejné) ...
    NewIcon = Signal()
    NewStatus = Signal()
    NewToolTip = Signal()

    def __init__(self, agent):
        self.agent = agent
        self.icon_name = ICON_AUTO_NAME
        self.status = "Active"

    # ... (Properties zůstávají stejné) ...
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
    def ToolTip(self): return (self.icon_name, [], "Asus Screen Toggle", f"Režim: {self.agent.mode}")
    @property
    def ItemIsMenu(self):
        return False

    # --- Methods ---

    def Activate(self, x, y):
        #print("SNI: Left Click -> MENU")
        """Levý klik: Zobrazíme menu."""
        # Nově: Voláme zobrazení menu
        GLib.idle_add(self.agent._show_gtk_menu, 1) # 1 = Levé tlačítko

    def ContextMenu(self, x, y):
        # print("SNI: Right Click -> MENU")
        # """Pravý klik: Zobrazíme menu."""
        GLib.idle_add(self.agent._show_gtk_menu, 3) # 3 = Pravé tlačítko

    def SecondaryActivate(self, x, y):
        """Střední klik (kolečko): Můžeme nechat tu rychlou kontrolu."""
        print("SNI: Middle Click -> Quick Check")
        self.agent._run_check("SNI_MiddleClick")

    # ... (Helpers set_icon/set_status zůstávají stejné) ...
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
        <method name="Quit"/>
      </interface>
    </node>
    """

    def __init__(self, quit_callback, bus):
        self.quit_callback = quit_callback
        self.mode = self._load_mode() # Načtení při startu
        self.bus = bus
        self.indicator = None
        self.tray_backend = None
        self.menu = None

        if is_kde():
            try:
                self._setup_sni()
                # tray_backend nastavíme až po úspěšné registraci v setup_sni
            except Exception as e:
                print(f"SNI selhalo, fallback na AppIndicator: {e}")
                self._setup_appindicator()
                self.tray_backend = "appindicator"
        else:
            self._setup_appindicator()
            self.tray_backend = "appindicator"

    # --- Práce se souborem ---
    def _load_mode(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
                        print(f"📂 Načten režim ze souboru: {mode}")
                        return mode
            except Exception as e:
                print(f"⚠️ Chyba při čtení configu: {e}")
        return "automatic-enabled"

    def _save_mode(self, mode):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                f.write(mode)
            print(f"💾 Režim '{mode}' uložen do {STATE_FILE}")
        except Exception as e:
            print(f"❌ Chyba při ukládání configu: {e}")

    # --- D-Bus Metody ---
    def Trigger(self):
        if self.mode != "automatic-enabled":
            print(f"📨 D-Bus: Ignorováno (Vynucen režim: {self.mode})")
            return f"IGNORED: Mode is {self.mode}"

        print("📨 D-Bus: Požadavek přijat (Auto).")
        self._run_check("D-Bus")
        return "OK"

    def SetMode(self, mode_str):
        if mode_str not in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
            return "ERROR: Invalid mode"

        # Projeví se to v GUI při příštím překreslení menu
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
            if self.mode == "automatic-enabled":
                self.sni.set_icon(ICON_AUTO_NAME)
            elif self.mode == "enforce-primary-only":
                self.sni.set_icon(ICON_PRIMARY_NAME)
            else:
                self.sni.set_icon(ICON_DESKTOP_NAME)
            return

        elif self.indicator: # AppIndicator backend
            icon_to_set = ICON_NAME
            if self.mode == "automatic-enabled":
                if os.path.exists(ICON_AUTO): icon_to_set = ICON_AUTO
                self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            elif self.mode == "enforce-primary-only":
                if os.path.exists(ICON_PRIMARY): icon_to_set = ICON_PRIMARY
                self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            else: # enforce-desktop
                if os.path.exists(ICON_DESKTOP): icon_to_set = ICON_DESKTOP
                self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)

            try:
                self.indicator.set_icon(icon_to_set)
            except:
                self.indicator.set_icon(ICON_NAME)

    def _on_mode_change(self, widget, mode_name):
        """Callback při změně přepínače v menu."""
        if widget.get_active():
            # 1. Změna v paměti
            self.mode = mode_name
            # 2. Uložení do souboru
            self._save_mode(mode_name)
            # 3. GUI Feedback (ikona)
            self._set_icon_by_mode()
            # 4. Akce
            self._run_check("MenuChange")

    def _build_menu(self):
        """
        Společná metoda pro vytvoření GTK Menu.
        Vrací objekt Gtk.Menu, který lze použít v AppIndicator i SNI.
        """
        menu = Gtk.Menu()

        item_title = Gtk.MenuItem(label="Asus Screen Control")
        item_title.set_sensitive(False)
        menu.append(item_title)
        menu.append(Gtk.SeparatorMenuItem())

        # --- Přepínače ---
        # 1. Automaticky
        radio_auto = Gtk.RadioMenuItem(label="🤖 Automaticky (Senzory)")
        radio_auto.connect("toggled", self._on_mode_change, "automatic-enabled")
        menu.append(radio_auto)

        group = radio_auto.get_group()

        # 2. Jen hlavní
        radio_primary = Gtk.RadioMenuItem(label="💻 Jen hlavní displej", group=group[0])
        radio_primary.connect("toggled", self._on_mode_change, "enforce-primary-only")
        menu.append(radio_primary)

        # 3. Oba
        radio_both = Gtk.RadioMenuItem(label="🖥️🖥️ Oba displeje", group=group[0])
        radio_both.connect("toggled", self._on_mode_change, "enforce-desktop")
        menu.append(radio_both)

        # Nastavení aktivního prvku podle aktuálního stavu self.mode
        # Toto je důležité hlavně pro SNI, které vytváří menu pokaždé znovu
        if self.mode == "automatic-enabled":
            radio_auto.set_active(True)
        elif self.mode == "enforce-primary-only":
            radio_primary.set_active(True)
        elif self.mode == "enforce-desktop":
            radio_both.set_active(True)

        menu.append(Gtk.SeparatorMenuItem())

        # 4. Položka: Zkontrolovat
        item_check = Gtk.MenuItem(label="Zkontrolovat")
        item_check.connect("activate", lambda _: self._run_check())
        menu.append(item_check)

        menu.append(Gtk.SeparatorMenuItem())

        # 5. Položka: Konec
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

        # Pro AppIndicator stačí menu vytvořit jednou
        menu = self._build_menu()
        self.indicator.set_menu(menu)

    def _setup_sni(self):
        print("🔵 Inicializuji KDE StatusNotifierItem (SNI)")
        self.sni = StatusNotifierItem(self)

        try:
            self.bus.register_object("/StatusNotifierItem", self.sni, None)
            self.tray_backend = "sni"
            self._set_icon_by_mode()
            print("✅ SNI objekt vytvořen (čekám na registraci jména).")
        except Exception as e:
            print(f"❌ Chyba při registraci SNI objektu: {e}")
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
                print(f"⚠️ Nepodařilo se kontaktovat KDE Watcher: {e}")

    def _show_gtk_menu(self, button):
        """Zobrazí GTK menu (voláno z SNI)."""
        # Uložíme menu do self, aby ho garbage collector nesmazal předčasně
        self.menu = self._build_menu()

        # Zobrazíme menu pod kurzorem myši.
        # Používáme čas 0 (Gtk.CURRENT_TIME), což řeší problémy
        # s mizením menu při volání z D-Bus/idle callbacku.
        self.menu.popup(None, None, None, None, button, 0)

        # Vrátíme False, aby se GLib.idle_add neopakovalo
        return False



def is_kde():
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "kde"

# --- Globální proměnné pro čistý shutdown ---
loop = None
publication = None

def quit_app(*args):
    global publication
    global loop

    """Hlavní funkce pro bezpečné ukončení."""
    print("\n🧹 Provádím úklid a ukončuji agenta...")

    # 1. Odhlášení z D-Bus
    if publication:
        try:
            publication.unpublish()
            publication = None
            print("   ✅ D-Bus jméno uvolněno.")
        except Exception as e:
            print(f"   ⚠️ Chyba při uvolňování D-Bus: {e}")

    # 2. Ukončení GTK smyčky
    if loop:
        Gtk.main_quit()
        
    sys.exit(0)

# --- Globální handler pro signály ---
def signal_handler():
    if agent.mode == "automatic-enabled":
        print("📩 Signál SIGUSR1 přijat!")
        agent._run_check("Signal")
    else:
        print(f"📩 Signál ignorován (Režim ze souboru: {agent.mode}).")
    return True

if __name__ == "__main__":
    # Singleton logika a start
    bus = SessionBus()

    # 1. Kontrola, zda už neběžíme
    dbus_sys = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
    if dbus_sys.NameHasOwner(BUS_NAME):
        print(f"⚠️ Agent už běží ({BUS_NAME})")
        sys.exit(0)

    # 2. Inicializace agenta (vytvoří objekty, ale nevolá Watchera)
    agent = AsusAgent(quit_callback=quit_app, bus=bus)

    try:
        # Uložíme si objekt publikace pro pozdější úklid
        publication = bus.publish(BUS_NAME, agent)
        print(f"✅ D-Bus jméno {BUS_NAME} získáno.")

        # 4. Registrace u KDE Watchera (teď už nás najde)
        agent.register_sni_watcher()

    except Exception as e:
        print("❌ publish selhal:")
        print(f"   typ: {type(e)}")
        print(f"   repr: {repr(e)}")
        print(f"   str : {e}")
        #traceback.print_exc()
        sys.exit(1)

    # Registrace signálů
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
