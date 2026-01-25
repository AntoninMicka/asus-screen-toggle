#!/usr/bin/env python3
import sys
import os
import subprocess
import gi
import gettext
import locale
import shutil

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

try:
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, GdkPixbuf
except ValueError:
    print(_("Error: Gtk 3.0 not found."))
    sys.exit(1)

# Pokus o import pydbus pro komunikaci s Agentem
try:
    from pydbus import SessionBus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    print(_("Warning: pydbus not found. Direct D-Bus communication disabled."))

# --- Konstanty ---
APP_TITLE = _("Nastavení Asus Screen Toggle")
BUS_NAME = "org.asus.ScreenToggle" # D-Bus jméno agenta
USER_SERVICE = "asus-screen-toggle.service"
SYSTEM_SERVICE = "asus-bottom-screen-init.service"
SYSTRAY_SERVICE = "asus-user-agent.service"

# Cesty ke konfiguracím
SYSTEM_CONFIG_FILE = "/etc/asus-screen-toggle.conf"
USER_CONFIG_FILE = os.path.expanduser("~/.config/asus-screen-toggle/user.conf")

# Cesty pro logiku přepínání (stejné jako v User Agent)
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")
SCRIPT_PATH = shutil.which("asus-check-keyboard-user") or "/usr/bin/asus-check-keyboard-user"

GENRULES_PATH = shutil.which("asus-check-keyboard-genrules") or "/usr/bin/asus-check-keyboard-genrules"

# Cesty k ikonám
ICON_PATH = "/usr/share/asus-screen-toggle"
ICON_AUTO = os.path.join(ICON_PATH, "icon-green.svg")
ICON_PRIMARY = os.path.join(ICON_PATH, "icon-red.svg")
ICON_DESKTOP = os.path.join(ICON_PATH, "icon-blue.svg")
ICON_TEMP = os.path.join(ICON_PATH, "icon-yellow.svg") # Dočasný režim (vytvoříme/přiřadíme)

class AsusSettingsApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_border_width(10)
        self.set_default_size(650, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.icon_map = {
            "automatic-enabled": "icon-green.svg",
            "enforce-desktop": "icon-blue.svg",
            "enforce-primary-only": "icon-red.svg",
            "temp-mirror": "icon-yellow.svg",
            "temp-reverse-mirror": "icon-yellow.svg",
            "temp-primary-only": "icon-yellow.svg"
        }

        # Notebook s kartami
        self.notebook = Gtk.Notebook()

        # Layout
        main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_layout)
        main_layout.pack_start(self.notebook, True, True, 0)

        # --- KARTA 0: DOMŮ (Rychlé ovládání) ---
        self.page_home = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.page_home.set_border_width(20)
        self.notebook.append_page(self.page_home, Gtk.Label(label="Domů"))

        # Nadpis
        lbl_welcome = Gtk.Label(label=_("<span size='x-large' weight='bold'>Rychlé ovládání</span>"))
        lbl_welcome.set_use_markup(True)
        self.page_home.pack_start(lbl_welcome, False, False, 10)

        hbox_modes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hbox_modes.set_halign(Gtk.Align.CENTER)
        self.page_home.pack_start(hbox_modes, True, True, 0)

        # 1. Tlačítko AUTO
        self.btn_mode_auto = self.create_mode_button(_("Automaticky"), ICON_AUTO, _("Senzory"), "automatic-enabled")
        hbox_modes.pack_start(self.btn_mode_auto, True, True, 0)

        # 2. Tlačítko PRIMARY
        self.btn_mode_primary = self.create_mode_button(_("Jen Hlavní"), ICON_PRIMARY, _("Vypnout spodní"), "enforce-primary-only")
        hbox_modes.pack_start(self.btn_mode_primary, True, True, 0)

        # 3. Tlačítko DESKTOP
        self.btn_mode_desktop = self.create_mode_button(_("Oba Displeje"), ICON_DESKTOP, _("Vynutit zapnutí"), "enforce-desktop")
        hbox_modes.pack_start(self.btn_mode_desktop, True, True, 0)

        # Oddělovač
        self.page_home.pack_start(Gtk.Separator(), False, False, 10)

        # Sekce pro dočasné režimy
        lbl_tmp = Gtk.Label(label=_("<span size='x-large' weight='bold'>Dočasné / Prezentační režimy:</span>\n<i>Tyto režimy se automaticky zruší po připojení klávesnice.</i>"))
        lbl_tmp.set_use_markup(True)
        self.page_home.pack_start(lbl_tmp, True, True, 0)

        hbox_tmp_modes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hbox_tmp_modes.set_halign(Gtk.Align.CENTER)
        self.page_home.pack_start(hbox_tmp_modes, True, True, 0)

        self.btn_mode_tmp_mirror = self.create_mode_button(_("Zrcadlení"), ICON_TEMP, _("Dočasné zrcadlení"), "temp-mirror")
        hbox_tmp_modes.pack_start(self.btn_mode_tmp_mirror, True, True, 0)

        self.btn_mode_tmp_reverse_mirror = self.create_mode_button(_("Otočené zrcadlení"), ICON_TEMP, _("Dočasné otočené zrcadlení"), "temp-reverse-mirror")
        hbox_tmp_modes.pack_start(self.btn_mode_tmp_reverse_mirror, True, True, 0)

        self.btn_mode_tmp_primary = self.create_mode_button(_("Jen Hlavní"), ICON_TEMP, _("Dočasný vypnout spodní"), "temp-primary-only")
        hbox_tmp_modes.pack_start(self.btn_mode_tmp_primary, True, True, 0)


        self.page_home.pack_start(Gtk.Separator(), False, False, 10)

        # Tlačítko Kontrola
        btn_check = Gtk.Button(label=_("🔄 Spustit okamžitou kontrolu"))
        btn_check.set_property("width-request", 300)
        btn_check.set_halign(Gtk.Align.CENTER)
        btn_check.get_style_context().add_class("suggested-action") # Modré zvýraznění
        btn_check.connect("clicked", lambda x: self.run_check())
        self.page_home.pack_start(btn_check, False, False, 10)

        # --- KARTA 1: OBECNÉ (Služby a uživatelské chování) ---
        self.page_general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.page_general.set_border_width(10)
        self.notebook.append_page(self.page_general, Gtk.Label(label=_("Služby & Config")))

        # 1. Sekce: Správa Služeb
        frame_services = Gtk.Frame(label=_("Stav Služeb"))
        self.page_general.pack_start(frame_services, False, False, 0)

        vbox_services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_services.set_border_width(10)
        frame_services.add(vbox_services)

        # User Service
        self.status_user = Gtk.Label(label="...")
        self.btn_user_toggle = Gtk.Button(label="...")
        self.btn_user_toggle.connect("clicked", self.on_user_service_toggle)
        self.switch_user_enable = Gtk.Switch()
        self.switch_user_enable.connect("notify::active", self.on_user_enable_toggle)
        vbox_services.pack_start(self.create_service_row(_("Uživatelská služba (Agent)"), self.status_user, self.btn_user_toggle, self.switch_user_enable), False, False, 0)

        vbox_services.pack_start(Gtk.Separator(), False, False, 5)
        self.status_systray = Gtk.Label(label="...")
        self.btn_systray_toggle = Gtk.Button(label="...")
        self.btn_systray_toggle.connect("clicked", self.on_systray_service_toggle)
        self.switch_systray_enable = Gtk.Switch()
        self.switch_systray_enable.connect("notify::active", self.on_systray_enable_toggle)
        vbox_services.pack_start(self.create_service_row(_("Indikátor stauu (Systray)"), self.status_systray, self.btn_systray_toggle, self.switch_systray_enable), False, False, 0)

        vbox_services.pack_start(Gtk.Separator(), False, False, 5)

        # System Service
        self.status_system = Gtk.Label(label="...")
        self.btn_system_toggle = Gtk.Button(label="...")
        self.btn_system_toggle.connect("clicked", self.on_system_service_toggle)
        self.switch_system_enable = Gtk.Switch()
        self.switch_system_enable.connect("notify::active", self.on_system_enable_toggle)
        vbox_services.pack_start(self.create_service_row(_("Systémová služba (Init)"), self.status_system, self.btn_system_toggle, self.switch_system_enable), False, False, 0)

        # 2. Sekce: Uživatelská konfigurace
        frame_user = Gtk.Frame(label=_("Uživatelská konfigurace"))
        self.page_general.pack_start(frame_user, False, False, 0)
        vbox_user = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_user.set_border_width(10)
        frame_user.add(vbox_user)

        lbl_info_user = Gtk.Label(label=_("<i>Ukládá se do ~/.config/asus-screen-toggle/config.conf</i>"), use_markup=True, xalign=0)
        vbox_user.pack_start(lbl_info_user, False, False, 5)

        self.user_chk_dbus = Gtk.CheckButton(label=_("Povolit D-Bus ovládání (ENABLE_DBUS)"))
        self.user_chk_signal = Gtk.CheckButton(label=_("Povolit reakci na signály/rotaci (ENABLE_SIGNAL)"))

        vbox_user.pack_start(self.user_chk_dbus, False, False, 0)
        vbox_user.pack_start(self.user_chk_signal, False, False, 0)


        # --- KARTA 2: HARDWARE (Systémová konfigurace) ---
        self.page_hw = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.page_hw.set_border_width(10)
        self.notebook.append_page(self.page_hw, Gtk.Label(label=_("Hardware (Systém)")))

        lbl_hw_info = Gtk.Label(label=_("<i>Tyto změny se zapíší do /etc/asus-screen-toggle.conf (vyžaduje root).</i>"), use_markup=True, xalign=0)
        self.page_hw.pack_start(lbl_hw_info, False, False, 0)

        # Checkbox pro systémové chování
        self.sys_chk_systemd = Gtk.CheckButton(label=_("Povolit Systemd ovládání (ENABLE_SYSTEMD_CALL)"))
        self.sys_chk_dbus = Gtk.CheckButton(label=_("Povolit D-Bus ovládání (ENABLE_DBUS)"))
        self.sys_chk_signal = Gtk.CheckButton(label=_("Povolit reakci na signály/rotaci (ENABLE_SIGNAL)"))
        self.sys_chk_direct = Gtk.CheckButton(label=_("Povolit přímé volání z Udev (ENABLE_DIRECT_CALL)"))
        self.page_hw.pack_start(self.sys_chk_dbus, False, False, 0)
        self.page_hw.pack_start(self.sys_chk_signal, False, False, 0)
        self.page_hw.pack_start(self.sys_chk_direct, False, False, 0)
        self.page_hw.pack_start(self.sys_chk_systemd, False, False, 0)
        self.page_hw.pack_start(Gtk.Separator(), False, False, 5)

        grid_hw = Gtk.Grid()
        grid_hw.set_column_spacing(10)
        grid_hw.set_row_spacing(10)
        self.page_hw.pack_start(grid_hw, False, False, 0)

        # Vytvoření vstupních polí
        self.entry_vendor = Gtk.Entry()
        self.entry_product = Gtk.Entry()
        self.entry_primary = Gtk.Entry()
        self.entry_secondary = Gtk.Entry()
        self.entry_lid = Gtk.Entry()

        row = 0
        self.add_config_row(grid_hw, row, _("Vendor ID:"), self.entry_vendor, _("Např. 0b05")); row+=1
        self.add_config_row(grid_hw, row, _("Product ID:"), self.entry_product, _("Např. 1bf2")); row+=1
        self.add_config_row(grid_hw, row, _("Hlavní displej:"), self.entry_primary, _("Např. eDP-1")); row+=1
        self.add_config_row(grid_hw, row, _("Sekundární displej:"), self.entry_secondary, _("Např. eDP-2")); row+=1
        self.add_config_row(grid_hw, row, _("Senzor víka:"), self.entry_lid, _("Např. LID nebo LID0")); row+=1

        # Propojení checkboxů pro okamžitou odezvu v UI
        self.sys_chk_dbus.connect("toggled", lambda w: self.user_chk_dbus.set_sensitive(w.get_active()))
        self.sys_chk_signal.connect("toggled", lambda w: self.user_chk_signal.set_sensitive(w.get_active()))

        # --- Spodní lišta tlačítek ---
        bbox = Gtk.ButtonBox(layout_style=Gtk.ButtonBoxStyle.END)
        main_layout.pack_end(bbox, False, False, 0)

        btn_refresh = Gtk.Button(label=_("Obnovit"))
        btn_refresh.connect("clicked", self.refresh_all)
        bbox.add(btn_refresh)

        btn_save = Gtk.Button(label=_("Uložit vše"))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        bbox.add(btn_save)

        #self.update_window_icon("automatic-enabled")
        # Start
        self.current_mode_in_ui = None # Pro sledování stavu UI
        self.refresh_all()
        GLib.timeout_add_seconds(3, self.refresh_services_only)

    # --- UI Helpers pro Domovskou stránku ---

    def create_mode_button(self, title, icon_path, subtitle, mode_id):
        """Vytvoří velké tlačítko s ikonou pro výběr režimu."""
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NORMAL)
        btn.set_size_request(140, 160) # Pevná velikost

        # Obsah tlačítka (Vertical Box)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_valign(Gtk.Align.CENTER)

        # Ikona
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 64, 64, True)
            img = Gtk.Image.new_from_pixbuf(pixbuf)
        except:
            img = Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

        vbox.pack_start(img, True, True, 5)

        # Texty
        lbl_title = Gtk.Label(label=f"<b>{title}</b>")
        lbl_title.set_use_markup(True)
        vbox.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label=f"<small>{subtitle}</small>")
        lbl_sub.set_use_markup(True)
        lbl_sub.get_style_context().add_class("dim-label")
        vbox.pack_start(lbl_sub, False, False, 0)

        btn.add(vbox)

        # Uložíme ID režimu do tlačítka pro callback
        btn.mode_id = mode_id
        btn.connect("clicked", self.on_mode_clicked)

        return btn

    def update_home_ui_state(self, current_mode):
        """Zvýrazní aktivní tlačítko podle režimu."""
        self.current_mode_in_ui = current_mode

        # Reset stylů (pomocí citlivosti - aktivní režim bude 'insensitive', tedy zamáčknutý)
        # Nebo lépe: Všechny sensitive, ale aktivnímu dáme jiný styl nebo relief.
        # Zde použijeme logiku: Aktivní tlačítko je "deaktivované" (nejde na něj znovu kliknout) a vypadá zamáčkle.

        for btn, mid in [(self.btn_mode_auto, "automatic-enabled"),
                         (self.btn_mode_primary, "enforce-primary-only"),
                         (self.btn_mode_desktop, "enforce-desktop"),
                         (self.btn_mode_tmp_primary, "temp-primary-only"),
                         (self.btn_mode_tmp_mirror, "temp-mirror"),
                         (self.btn_mode_tmp_reverse_mirror, "temp-reverse-mirror")]:
            if mid == current_mode:
                btn.set_sensitive(False) # Vizuálně indikuje "vybráno"
                # btn.get_style_context().add_class("suggested-action") # Alternativa pro GTK CSS
            else:
                btn.set_sensitive(True)

        # Okamžitá vizuální zpětná vazba v okně
        self.update_window_icon(current_mode)

    def on_mode_clicked(self, btn):
        mode = btn.mode_id
        print(_(f"UI: Požadavek na změnu režimu -> {mode}"))

        success = False

        # 1. Zkusit D-Bus (synchronizace s Agentem)
        if DBUS_AVAILABLE and self.user_chk_dbus.get_active():
            try:
                bus = SessionBus()
                # Získáme proxy objekt
                agent_proxy = bus.get(BUS_NAME) # Získá hlavní object path
                # Voláme metodu SetMode
                resp = agent_proxy.SetMode(mode)
                print(_(f"D-Bus odpověď: {resp}"))
                success = True
            except Exception as e:
                print(_(f"D-Bus chyba (Agent neběží?): {e}"))

        if not success:
            import os
            print(_(f"systemd volani {mode}"))
            try:
                os.system("systemctl --user start asus-screen-toggle.service > /dev/null 2>&1")
                os.makedirs(STATE_DIR, exist_ok=True)
                with open(STATE_FILE, 'w') as f:
                    f.write(mode)
            except Exception as e:
                self.show_error(_(f"Nepodařilo se zapsat stav: {e}"))
                return

        # 2. Fallback: Zápis do souboru (pokud D-Bus selhal)
        if not success:
            print(_("Fallback: Zapisuji přímo do souboru..."))
            try:
                os.makedirs(STATE_DIR, exist_ok=True)
                with open(STATE_FILE, 'w') as f:
                    f.write(mode)
                self.run_check() # Spustíme script manuálně
            except Exception as e:
                self.show_error(_(f"Nepodařilo se zapsat stav: {e}"))
                return

        # UI aktualizujeme hned pro odezvu (timer to pak potvrdí)
        self.update_home_ui_state(mode)

    def run_check(self):
        try:
            subprocess.Popen([SCRIPT_PATH])
        except Exception as e:
            self.show_error(_(f"Chyba při spouštění skriptu: {e}"))

    def periodic_refresh(self):
        self.refresh_all()
        return True # Pokračovat v timeru

    def refresh_all(self, widget=None):
        # 1. Režim (čtení ze souboru - synchronizace od Agenta k Aplikaci)
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode != self.current_mode_in_ui:
                        self.update_home_ui_state(mode)
            except: pass

        # 2. Configy
        self.load_configs()
        # 3. Služby
        self.refresh_services_only()

    # ... (Zbytek kódu: create_service_row, load_configs, on_save_clicked atd. zůstává stejný) ...

    # Pro úplnost kopíruji zkráceně zbytek metod, aby soubor byl kompletní:

    def create_service_row(self, title, label_status, btn_toggle, switch_enable):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_size_request(200, -1)
        row.pack_start(lbl, False, False, 0)
        row.pack_start(label_status, True, True, 0)
        row.pack_start(btn_toggle, False, False, 0)
        row.pack_start(Gtk.Label(label=_("Boot:")), False, False, 0)
        row.pack_start(switch_enable, False, False, 0)
        return row

    def add_config_row(self, grid, row, label_text, entry_widget, placeholder):
        lbl = Gtk.Label(label=label_text, xalign=1)
        entry_widget.set_placeholder_text(placeholder)
        entry_widget.set_hexpand(True)
        grid.attach(lbl, 0, row, 1, 1)
        grid.attach(entry_widget, 1, row, 1, 1)

    def refresh_services_only(self):
        active, enabled = self.get_service_status(USER_SERVICE, user=True)
        self.update_service_ui(self.status_user, self.btn_user_toggle, self.switch_user_enable, active, enabled)

        active, enabled = self.get_service_status(SYSTRAY_SERVICE, user=True)
        self.update_service_ui(self.status_systray, self.btn_systray_toggle, self.switch_systray_enable, active, enabled)

        active, enabled = self.get_service_status(SYSTEM_SERVICE, user=False)
        self.update_service_ui(self.status_system, self.btn_system_toggle, self.switch_system_enable, active, enabled)
        return True

    def get_service_status(self, service, user=True):
        cmd = ["systemctl"]
        if user: cmd.append("--user")

        res_act = subprocess.run(cmd + ["is-active", service], stdout=subprocess.PIPE, text=True)
        res_en = subprocess.run(cmd + ["is-enabled", service], stdout=subprocess.PIPE, text=True)
        return (res_act.stdout.strip() == _("active"), res_en.stdout.strip() == _("enabled"))

    def update_service_ui(self, label, button, switch, active, enabled):
        switch.handler_block_by_func(self.on_user_enable_toggle if switch == self.switch_user_enable else self.on_system_enable_toggle if switch == self.switch_system_enable else self.on_systray_enable_toggle)
        switch.set_active(enabled)
        switch.handler_unblock_by_func(self.on_user_enable_toggle if switch == self.switch_user_enable else self.on_system_enable_toggle if switch == self.switch_system_enable else self.on_systray_enable_toggle)

        if active:
            label.set_markup(_("<span foreground='green'><b>Běží</b></span>"))
            button.set_label(_("Zastavit"))
        else:
            label.set_markup(_("<span foreground='red'>Zastaveno</span>"))
            button.set_label(_("Spustit"))

    def update_window_icon(self, mode):
        icon_name = self.icon_map.get(mode, "icon-green.svg")
        icon_path = os.path.join("/usr/share/asus-screen-toggle", icon_name)

        if os.path.exists(icon_path):
            try:
                # self.set_icon_from_file(icon_path)
                app.set_icon_name(icon_path)
            except Exception as e:
                print(f"Nepodařilo se nastavit ikonu okna: {e}")

    def load_configs(self):
        # 1. Načíst SYSTÉMOVÉ nastavení (defaulty + /etc)
        sys_data = {
            "VENDOR_ID": "0b05", "PRODUCT_ID": "1bf2",
            "PRIMARY_DISPLAY_NAME": "eDP-1", "SECONDARY_DISPLAY_NAME": "eDP-2",
            "LID": "LID",
            "ENABLE_DIRECT_CALL": True,
            "ENABLE_DBUS": True, "ENABLE_SIGNAL": True, "ENABLE_SYSTEMD_CALL": True
        }

        if os.path.exists(SYSTEM_CONFIG_FILE):
            sys_data.update(self._parse_config_file(SYSTEM_CONFIG_FILE))

        # Aplikace do GUI - Hardware a Systém
        self.entry_vendor.set_text(str(sys_data.get("VENDOR_ID", "")))
        self.entry_product.set_text(str(sys_data.get("PRODUCT_ID", "")))
        self.entry_primary.set_text(str(sys_data.get("PRIMARY_DISPLAY_NAME", "")))
        self.entry_secondary.set_text(str(sys_data.get("SECONDARY_DISPLAY_NAME", "")))
        self.entry_lid.set_text(str(sys_data.get("LID", "")))

        # Systémové checkboxy
        sys_dbus_active = sys_data.get("ENABLE_DBUS") is True
        sys_signal_active = sys_data.get("ENABLE_SIGNAL") is True
        sys_systemd_active = sys_data.get("ENABLE_SYSTEMD_CALL") is True

        self.sys_chk_direct.set_active(sys_data.get("ENABLE_DIRECT_CALL") is True)
        self.sys_chk_dbus.set_active(sys_dbus_active)
        self.sys_chk_signal.set_active(sys_signal_active)
        self.sys_chk_systemd.set_active(sys_systemd_active)

        # 2. Načíst UŽIVATELSKÉ nastavení
        user_data = {}
        if os.path.exists(USER_CONFIG_FILE):
            user_data = self._parse_config_file(USER_CONFIG_FILE)

        # Logika AND detekovaná přímo v UI:
        # Pokud je SYSTÉM False, uživatel nesmí zapnout.

        # DBUS
        user_dbus_val = user_data.get("ENABLE_DBUS", sys_dbus_active)
        self.user_chk_dbus.set_active(user_dbus_val and sys_dbus_active)
        self.user_chk_dbus.set_sensitive(sys_dbus_active) # Zašedne, pokud systém zakázal

        # SIGNAL
        user_signal_val = user_data.get("ENABLE_SIGNAL", sys_signal_active)
        self.user_chk_signal.set_active(user_signal_val and sys_signal_active)
        self.user_chk_signal.set_sensitive(sys_signal_active) # Zašedne, pokud systém zakázal

        # Bonus: tooltip pro vysvětlení
        if not sys_signal_active:
            self.user_chk_signal.set_tooltip_text(_("Zakázáno správcem v /etc/asus-screen-toggle.conf"))


    def _parse_config_file(self, filepath):
        data = {}
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line: continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().replace('"', '')

                    if val.lower() == "true": data[key] = True
                    elif val.lower() == "false": data[key] = False
                    else: data[key] = val
        except: pass
        return data

    # --- Logika ukládání ---
    def on_save_clicked(self, widget):
        # 1. ULOŽENÍ UŽIVATELSKÉHO CONFIGU (~/.config)
        # Zde ukládáme POUZE preference chování
        try:
            os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
            with open(USER_CONFIG_FILE, 'w') as f:
                f.write(_("# Uživatelská konfigurace Asus Screen Toggle\n"))
                f.write(f"ENABLE_DBUS={'true' if self.user_chk_dbus.get_active() else 'false'}\n")
                f.write(f"ENABLE_SIGNAL={'true' if self.user_chk_signal.get_active() else 'false'}\n")
        except Exception as e:
            self.show_error(_(f"Nepodařilo se uložit uživatelský config: {e}"))
            return

        # 2. ULOŽENÍ SYSTÉMOVÉHO CONFIGU (/etc)
        # Zde ukládáme Hardware a Direct Call
        sys_content = [
            _("# Vygenerováno Asus Screen Settings - Systémová konfigurace"),
            f'VENDOR_ID="{self.entry_vendor.get_text()}"',
            f'PRODUCT_ID="{self.entry_product.get_text()}"',
            f'PRIMARY_DISPLAY_NAME="{self.entry_primary.get_text()}"',
            f'SECONDARY_DISPLAY_NAME="{self.entry_secondary.get_text()}"',
            f'LID="{self.entry_lid.get_text()}"',
            "",
            f'ENABLE_DIRECT_CALL={"true" if self.sys_chk_direct.get_active() else "false"}',
            f'ENABLE_DBUS={"true" if self.sys_chk_dbus.get_active() else "false"}',
            f'ENABLE_SIGNAL={"true" if self.sys_chk_signal.get_active() else "false"}',
            f'ENABLE_SYSTEMD_CALL={"true" if self.sys_chk_systemd.get_active() else "false"}',
        ]

        file_content = "\n".join(sys_content)

        # Uložení přes pkexec
        cmd = f"cat <<EOF > /tmp/asus_conf_tmp\n{file_content}\nEOF\n"
        cmd += f"pkexec mv /tmp/asus_conf_tmp {SYSTEM_CONFIG_FILE}"

        try:
            # A) Samotné uložení souboru
            subprocess.run(["bash", "-c", cmd], check=True)

            # B) Dotaz na přegenerování pravidel (pouze pokud se uložení povedlo)
            confirm = Gtk.MessageDialog(transient_for=self, flags=0,
                                      message_type=Gtk.MessageType.QUESTION,
                                      buttons=Gtk.ButtonsType.YES_NO,
                                      text=_("Aktualizovat Udev pravidla?"))
            confirm.format_secondary_text(
                _("Změnili jste systémové nastavení. Pro správnou funkčnost detekce hardwaru "
                "je třeba přegenerovat a načíst pravidla Udev.\n\n"
                "Chcete to provést nyní? (Vyžaduje heslo)")
            )
            response = confirm.run()
            confirm.destroy()

            if response == Gtk.ResponseType.YES:
                try:
                    # Sestavíme řetězec příkazů:
                    # 1. Spustit generovací skript
                    # 2. Reloadnout pravidla (pokud 1. prošla)
                    # 3. Triggerovat události (pokud 2. prošla)
                    full_cmd = (
                        "&GENRULES_PATH && "
                        "udevadm control --reload-rules && "
                        "udevadm trigger"
                    )

                    # Spustíme vše pod jedním pkexec (jedno heslo)
                    subprocess.run(["pkexec", "bash", "-c", full_cmd], check=True)

                except subprocess.CalledProcessError:
                     self.show_error(_("Nepodařilo se přegenerovat a aplikovat pravidla."))

            # C) Restart agenta (aby načetl případné změny v logice)
            subprocess.run(["systemctl", "--user", "kill", "-s", "HUP", USER_SERVICE])

            # Finální info
            msg = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO,
                                  buttons=Gtk.ButtonsType.OK, text=_("Hotovo"))
            msg.format_secondary_text(_("Konfigurace byla úspěšně uložena."))
            msg.run()
            msg.destroy()

        except subprocess.CalledProcessError:
            self.show_error(_("Nepodařilo se uložit systémovou konfiguraci (zamítnuto)."))

    # --- Handlery Služeb ---
    def on_user_service_toggle(self, btn):
        action = "stop" if btn.get_label() == _("Zastavit") else "start"
        subprocess.run(["systemctl", "--user", action, USER_SERVICE])
        self.refresh_services_only()

    def on_systray_service_toggle(self, btn):
        action = "stop" if btn.get_label() == _("Zastavit") else "start"
        subprocess.run(["systemctl", "--user", action, SYSTRAY_SERVICE])
        self.refresh_services_only()

    def on_user_enable_toggle(self, switch, gparam):
        action = "enable" if switch.get_active() else "disable"
        subprocess.run(["systemctl", "--user", action, USER_SERVICE])
        self.refresh_services_only()

    def on_systray_enable_toggle(self, switch, gparam):
        action = "enable" if switch.get_active() else "disable"
        subprocess.run(["systemctl", "--user", action, SYSTRAY_SERVICE])
        self.refresh_services_only()

    def on_system_service_toggle(self, btn):
        action = "stop" if btn.get_label() == "Zastavit" else "start"
        subprocess.run(["pkexec", "systemctl", action, SYSTEM_SERVICE])
        self.refresh_services_only()

    def on_system_enable_toggle(self, switch, gparam):
        action = "enable" if switch.get_active() else "disable"
        subprocess.run(["pkexec", "systemctl", action, SYSTEM_SERVICE])
        self.refresh_services_only()

    def show_error(self, message):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=_("Chyba"))
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    app = AsusSettingsApp()
    app.set_icon_from_file(ICON_DESKTOP)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
