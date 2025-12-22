#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import warnings

# Potlačení warningů
warnings.filterwarnings("ignore")

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
ICON_AUTO = os.path.join(ICON_PATH, "icon-green.svg")
ICON_PRIMARY = os.path.join(ICON_PATH, "icon-red.svg")
ICON_DESKTOP = os.path.join(ICON_PATH, "icon-blue.svg")

# Cesta k souboru s nastavením
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")

class AsusAgent:
    """
    D-Bus Agent s perzistencí do souboru.
    """

    def __init__(self, quit_callback):
        # OPRAVA: Přidán argument quit_callback
        self.quit_callback = quit_callback
        self.mode = self._load_mode() # Načtení při startu
        self.indicator = None
        self._setup_systray()

    # --- Práce se souborem ---
    def _load_mode(self):
        """Načte režim ze souboru, default je 'automatic-enabled'."""
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
        """Uloží režim do souboru."""
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                f.write(mode)
            print(f"💾 Režim '{mode}' uložen do {STATE_FILE}")
        except Exception as e:
            print(f"❌ Chyba při ukládání configu: {e}")

    # --- D-Bus Metody ---
    def Trigger(self):
        # I při triggeru přes D-Bus se podíváme, co máme nastaveno
        if self.mode != "automatic-enabled":
            print(f"📨 D-Bus: Ignorováno (Vynucen režim: {self.mode})")
            return f"IGNORED: Mode is {self.mode}"

        print("📨 D-Bus: Požadavek přijat (Auto).")
        self._run_check("D-Bus")
        return "OK"

    def SetMode(self, mode_str):
        if mode_str not in ["automatic-enabled", "enforce-primary-only", "enforce-desktop"]:
            return "ERROR: Invalid mode"

        # Aktualizace GUI (to vyvolá callback _on_mode_change a uloží soubor)
        if mode_str == "automatic-enabled":
            self.radio_auto.set_active(True)
        elif mode_str == "enforce-primary-only":
            self.radio_primary.set_active(True)
        elif mode_str == "enforce-desktop":
            self.radio_both.set_active(True)

        return f"OK: Switched to {mode_str}"

    def Quit(self):
        print("🛑 Požadavek na ukončení...")
        # OPRAVA: Voláme callback pro čistý úklid (D-Bus unpublish)
        self.quit_callback()

    # --- Interní logika ---
    def _run_check(self, source="Internal"):
        """Spustí kontrolní skript."""
        print(f"🚀 Spouštím logiku (Režim: {self.mode}, Zdroj: {source})...")
        try:
            # Už nepředáváme ENV proměnnou, skript si přečte soubor sám!
            subprocess.Popen([SCRIPT_PATH])
        except FileNotFoundError:
            print(f"❌ Chyba: Skript {SCRIPT_PATH} nebyl nalezen.")

    def _set_icon_by_mode(self):
        """Pomocná metoda pro nastavení ikony (pro AppIndicator)."""
        # Poznámka: set_icon obvykle bere název ze systémového tématu.
        # Pokud chceme cestu k souboru, některé verze to umí přímo,
        # jiné vyžadují set_icon_full nebo set_icon_theme_path.
        # Zkusíme předat cestu, pokud existuje.

        icon_to_set = ICON_NAME # Fallback

        if self.mode == "automatic-enabled":
            if os.path.exists(ICON_AUTO): icon_to_set = ICON_AUTO
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        elif self.mode == "enforce-primary-only":
            if os.path.exists(ICON_PRIMARY): icon_to_set = ICON_PRIMARY
            self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)
        else: # enforce-desktop
            if os.path.exists(ICON_DESKTOP): icon_to_set = ICON_DESKTOP
            self.indicator.set_status(AppIndicator.IndicatorStatus.ATTENTION)

        # Nastavení ikony
        try:
            self.indicator.set_icon(icon_to_set)
        except:
            # Fallback pro starší verze nebo pokud cesta nefunguje
            self.indicator.set_icon(ICON_NAME)

    def _on_mode_change(self, widget, mode_name):
        """Callback při změně přepínače v menu."""
        if widget.get_active():
            # 1. Změna v paměti
            self.mode = mode_name
            # 2. Uložení do souboru
            self._save_mode(mode_name)

            # 3. GUI Feedback
            self._set_icon_by_mode()

            # 4. Okamžité provedení akce
            self._run_check("MenuChange")

    def _setup_systray(self):
        self.indicator = AppIndicator.Indicator.new(
            APP_ID, ICON_NAME, AppIndicator.IndicatorCategory.HARDWARE
        )

        # Nastavení ikony při startu
        self._set_icon_by_mode()

        menu = Gtk.Menu()

        item_title = Gtk.MenuItem(label="Asus Screen Control")
        item_title.set_sensitive(False)
        menu.append(item_title)
        menu.append(Gtk.SeparatorMenuItem())

        # --- Přepínače ---
        # Vytvoříme první
        self.radio_auto = Gtk.RadioMenuItem(label="🤖 Automaticky (Senzory)")
        self.radio_auto.connect("toggled", self._on_mode_change, "automatic-enabled")
        menu.append(self.radio_auto)

        group = self.radio_auto.get_group()

        self.radio_primary = Gtk.RadioMenuItem(label="💻 Jen hlavní displej", group=group[0])
        self.radio_primary.connect("toggled", self._on_mode_change, "enforce-primary-only")
        menu.append(self.radio_primary)

        # OPRAVA: Sjednocen název režimu na 'enforce-desktop' místo 'both'
        self.radio_both = Gtk.RadioMenuItem(label="🖥️🖥️ Oba displeje", group=group[0])
        self.radio_both.connect("toggled", self._on_mode_change, "enforce-desktop")
        menu.append(self.radio_both)

        # Nastavení aktivního prvku podle načteného stavu
        if self.mode == "automatic-enabled":
            self.radio_auto.set_active(True)
        elif self.mode == "enforce-primary-only":
            self.radio_primary.set_active(True)
        elif self.mode == "enforce-desktop":
            self.radio_both.set_active(True)

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
        self.indicator.set_menu(menu)


# --- Globální proměnné pro čistý shutdown ---
loop = None
publication = None

def quit_app(*args):
    """Hlavní funkce pro bezpečné ukončení."""
    print("\n🧹 Provádím úklid a ukončuji agenta...")

    # 1. Odhlášení z D-Bus
    if publication:
        try:
            publication.unpublish()
            print("   ✅ D-Bus jméno uvolněno.")
        except Exception as e:
            print(f"   ⚠️ Chyba při uvolňování D-Bus: {e}")

    # 2. Ukončení GTK smyčky
    if loop:
        Gtk.main_quit()

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

    # Předáme funkci quit_app do agenta, aby ji mohl volat z menu
    # OPRAVA: Třída AsusAgent nyní tento argument přijímá
    agent = AsusAgent(quit_callback=quit_app)

    try:
        # Uložíme si objekt publikace pro pozdější úklid
        publication = bus.publish(BUS_NAME, agent)
    except RuntimeError:
        print(f"⚠️ Agent už běží (Jméno {BUS_NAME} je obsazené).")
        sys.exit(0)

    # Registrace signálů
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, signal_handler)

    # ZDE JE ZMĚNA: SIGTERM a SIGINT (Ctrl+C) nyní volají naši čistící funkci
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
