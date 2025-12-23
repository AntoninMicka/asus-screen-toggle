#!/usr/bin/env python3
import sys
import os
import subprocess
import gi

try:
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
except ValueError:
    print("Error: Gtk 3.0 not found.")
    sys.exit(1)

# --- Konstanty ---
APP_TITLE = "Nastavení Asus Screen Toggle"
USER_SERVICE = "asus-screen-toggle.service"
SYSTEM_SERVICE = "asus-bottom-screen-init.service"

USER_CONFIG_FILE = os.path.expanduser("~/.config/asus-screen-toggle/config.conf")
SYSTEM_CONFIG_FILE = "/etc/asus-check-keyboard.cfg"

class AsusSettingsApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_border_width(10)
        self.set_default_size(600, 550)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Notebook s kartami
        self.notebook = Gtk.Notebook()

        # Layout
        main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_layout)
        main_layout.pack_start(self.notebook, True, True, 0)

        # --- KARTA 1: OBECNÉ (Služby a uživatelské chování) ---
        self.page_general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.page_general.set_border_width(10)
        self.notebook.append_page(self.page_general, Gtk.Label(label="Obecné & Služby"))

        # 1. Sekce: Správa Služeb
        frame_services = Gtk.Frame(label="Stav Služeb")
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
        vbox_services.pack_start(self.create_service_row("Uživatelská služba (Agent)", self.status_user, self.btn_user_toggle, self.switch_user_enable), False, False, 0)

        vbox_services.pack_start(Gtk.Separator(), False, False, 5)

        # System Service
        self.status_system = Gtk.Label(label="...")
        self.btn_system_toggle = Gtk.Button(label="...")
        self.btn_system_toggle.connect("clicked", self.on_system_service_toggle)
        self.switch_system_enable = Gtk.Switch()
        self.switch_system_enable.connect("notify::active", self.on_system_enable_toggle)
        vbox_services.pack_start(self.create_service_row("Systémová služba (Init)", self.status_system, self.btn_system_toggle, self.switch_system_enable), False, False, 0)

        # 2. Sekce: Uživatelská konfigurace
        frame_user = Gtk.Frame(label="Uživatelská konfigurace")
        self.page_general.pack_start(frame_user, False, False, 0)
        vbox_user = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_user.set_border_width(10)
        frame_user.add(vbox_user)

        lbl_info_user = Gtk.Label(label="<i>Ukládá se do ~/.config/asus-screen-toggle/config.conf</i>", use_markup=True, xalign=0)
        vbox_user.pack_start(lbl_info_user, False, False, 5)

        self.user_chk_dbus = Gtk.CheckButton(label="Povolit D-Bus ovládání (ENABLE_DBUS)")
        self.user_chk_signal = Gtk.CheckButton(label="Povolit reakci na signály/rotaci (ENABLE_SIGNAL)")

        vbox_user.pack_start(self.user_chk_dbus, False, False, 0)
        vbox_user.pack_start(self.user_chk_signal, False, False, 0)


        # --- KARTA 2: HARDWARE (Systémová konfigurace) ---
        self.page_hw = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.page_hw.set_border_width(10)
        self.notebook.append_page(self.page_hw, Gtk.Label(label="Hardware (Systém)"))

        lbl_hw_info = Gtk.Label(label="<i>Tyto změny se zapíší do /etc/asus-screen-toggle.conf (vyžaduje root).</i>", use_markup=True, xalign=0)
        self.page_hw.pack_start(lbl_hw_info, False, False, 0)

        # Checkbox pro systémové chování
        self.sys_chk_dbus = Gtk.CheckButton(label="Povolit D-Bus ovládání (ENABLE_DBUS)")
        self.sys_chk_signal = Gtk.CheckButton(label="Povolit reakci na signály/rotaci (ENABLE_SIGNAL)")
        self.sys_chk_direct = Gtk.CheckButton(label="Povolit přímé volání z Udev (ENABLE_DIRECT_CALL)")
        self.page_hw.pack_start(self.sys_chk_dbus, False, False, 0)
        self.page_hw.pack_start(self.sys_chk_signal, False, False, 0)
        self.page_hw.pack_start(self.sys_chk_direct, False, False, 0)

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
        self.add_config_row(grid_hw, row, "Vendor ID:", self.entry_vendor, "Např. 0b05"); row+=1
        self.add_config_row(grid_hw, row, "Product ID:", self.entry_product, "Např. 1bf2"); row+=1
        self.add_config_row(grid_hw, row, "Hlavní displej:", self.entry_primary, "Např. eDP-1"); row+=1
        self.add_config_row(grid_hw, row, "Sekundární displej:", self.entry_secondary, "Např. eDP-2"); row+=1
        self.add_config_row(grid_hw, row, "Senzor víka:", self.entry_lid, "Např. LID nebo LID0"); row+=1


        # --- Spodní lišta tlačítek ---
        bbox = Gtk.ButtonBox(layout_style=Gtk.ButtonBoxStyle.END)
        main_layout.pack_end(bbox, False, False, 0)

        btn_refresh = Gtk.Button(label="Obnovit")
        btn_refresh.connect("clicked", self.refresh_all)
        bbox.add(btn_refresh)

        btn_save = Gtk.Button(label="Uložit vše")
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        bbox.add(btn_save)

        # Start
        self.refresh_all()
        GLib.timeout_add_seconds(3, self.refresh_services_only)

    def create_service_row(self, title, label_status, btn_toggle, switch_enable):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_size_request(200, -1)
        row.pack_start(lbl, False, False, 0)
        row.pack_start(label_status, True, True, 0)
        row.pack_start(btn_toggle, False, False, 0)
        row.pack_start(Gtk.Label(label="Boot:"), False, False, 0)
        row.pack_start(switch_enable, False, False, 0)
        return row

    def add_config_row(self, grid, row, label_text, entry_widget, placeholder):
        lbl = Gtk.Label(label=label_text, xalign=1)
        entry_widget.set_placeholder_text(placeholder)
        entry_widget.set_hexpand(True)
        grid.attach(lbl, 0, row, 1, 1)
        grid.attach(entry_widget, 1, row, 1, 1)

    # --- Logika načítání ---
    def refresh_all(self, widget=None):
        self.load_configs()
        self.refresh_services_only()

    def refresh_services_only(self):
        active, enabled = self.get_service_status(USER_SERVICE, user=True)
        self.update_service_ui(self.status_user, self.btn_user_toggle, self.switch_user_enable, active, enabled)

        active, enabled = self.get_service_status(SYSTEM_SERVICE, user=False)
        self.update_service_ui(self.status_system, self.btn_system_toggle, self.switch_system_enable, active, enabled)
        return True

    def get_service_status(self, service, user=True):
        cmd = ["systemctl"]
        if user: cmd.append("--user")

        res_act = subprocess.run(cmd + ["is-active", service], stdout=subprocess.PIPE, text=True)
        res_en = subprocess.run(cmd + ["is-enabled", service], stdout=subprocess.PIPE, text=True)
        return (res_act.stdout.strip() == "active", res_en.stdout.strip() == "enabled")

    def update_service_ui(self, label, button, switch, active, enabled):
        switch.handler_block_by_func(self.on_user_enable_toggle if switch == self.switch_user_enable else self.on_system_enable_toggle)
        switch.set_active(enabled)
        switch.handler_unblock_by_func(self.on_user_enable_toggle if switch == self.switch_user_enable else self.on_system_enable_toggle)

        if active:
            label.set_markup("<span foreground='green'><b>Běží</b></span>")
            button.set_label("Zastavit")
        else:
            label.set_markup("<span foreground='red'>Zastaveno</span>")
            button.set_label("Spustit")

    def load_configs(self):
        # 1. Načíst SYSTÉMOVÉ nastavení (defaulty + /etc)
        sys_data = {
            "VENDOR_ID": "0b05", "PRODUCT_ID": "1bf2",
            "PRIMARY_DISPLAY_NAME": "eDP-1", "SECONDARY_DISPLAY_NAME": "eDP-2",
            "LID": "LID",
            "ENABLE_DIRECT_CALL": True,
            # Tyto hodnoty slouží jako default, pokud uživatel nemá svůj config
            "ENABLE_DBUS": True, "ENABLE_SIGNAL": True
        }

        if os.path.exists(SYSTEM_CONFIG_FILE):
            sys_data.update(self._parse_config_file(SYSTEM_CONFIG_FILE))

        # Aplikace do GUI - Hardware a Systém
        self.entry_vendor.set_text(str(sys_data.get("VENDOR_ID", "")))
        self.entry_product.set_text(str(sys_data.get("PRODUCT_ID", "")))
        self.entry_primary.set_text(str(sys_data.get("PRIMARY_DISPLAY_NAME", "")))
        self.entry_secondary.set_text(str(sys_data.get("SECONDARY_DISPLAY_NAME", "")))
        self.entry_lid.set_text(str(sys_data.get("LID", "")))
        self.sys_chk_direct.set_active(sys_data.get("ENABLE_DIRECT_CALL") is True)
        self.sys_chk_dbus.set_active(sys_data.get("ENABLE_DBUS") is True)
        self.sys_chk_signal.set_active(sys_data.get("ENABLE_SIGNAL") is True)

        # 2. Načíst UŽIVATELSKÉ nastavení (přebíjí systémové pro DBUS/SIGNAL)
        user_data = {}
        if os.path.exists(USER_CONFIG_FILE):
            user_data = self._parse_config_file(USER_CONFIG_FILE)

        # Aplikace do GUI - User Checkboxy
        # Použijeme hodnotu z user_data, pokud není, bereme ze sys_data (default)
        dbus_val = user_data.get("ENABLE_DBUS", sys_data.get("ENABLE_DBUS"))
        signal_val = user_data.get("ENABLE_SIGNAL", sys_data.get("ENABLE_SIGNAL"))

        self.user_chk_dbus.set_active(dbus_val is True)
        self.user_chk_signal.set_active(signal_val is True)


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
                f.write("# Uživatelská konfigurace Asus Screen Toggle\n")
                f.write(f"ENABLE_DBUS={'true' if self.user_chk_dbus.get_active() else 'false'}\n")
                f.write(f"ENABLE_SIGNAL={'true' if self.user_chk_signal.get_active() else 'false'}\n")
        except Exception as e:
            self.show_error(f"Nepodařilo se uložit uživatelský config: {e}")
            return

        # 2. ULOŽENÍ SYSTÉMOVÉHO CONFIGU (/etc)
        # Zde ukládáme Hardware a Direct Call
        sys_content = [
            "# Vygenerováno Asus Screen Settings - Systémová konfigurace",
            f'VENDOR_ID="{self.entry_vendor.get_text()}"',
            f'PRODUCT_ID="{self.entry_product.get_text()}"',
            f'PRIMARY_DISPLAY_NAME="{self.entry_primary.get_text()}"',
            f'SECONDARY_DISPLAY_NAME="{self.entry_secondary.get_text()}"',
            f'LID="{self.entry_lid.get_text()}"',
            "",
            f'ENABLE_DIRECT_CALL={"true" if self.sys_chk_direct.get_active() else "false"}',
            f'ENABLE_DBUS={"true" if self.sys_chk_dbus.get_active() else "false"}',
            f'ENABLE_SIGNAL={"true" if self.sys_chk_signal.get_active() else "false"}',
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
                                      text="Aktualizovat Udev pravidla?")
            confirm.format_secondary_text(
                "Změnili jste systémové nastavení. Pro správnou funkčnost detekce hardwaru "
                "je třeba přegenerovat a načíst pravidla Udev.\n\n"
                "Chcete to provést nyní? (Vyžaduje heslo)"
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
                        "/usr/bin/asus-check-keyboard-genrules.sh && "
                        "udevadm control --reload-rules && "
                        "udevadm trigger"
                    )

                    # Spustíme vše pod jedním pkexec (jedno heslo)
                    subprocess.run(["pkexec", "bash", "-c", full_cmd], check=True)

                except subprocess.CalledProcessError:
                     self.show_error("Nepodařilo se přegenerovat a aplikovat pravidla.")

            # C) Restart agenta (aby načetl případné změny v logice)
            subprocess.run(["systemctl", "--user", "kill", "-s", "HUP", USER_SERVICE])

            # Finální info
            msg = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO,
                                  buttons=Gtk.ButtonsType.OK, text="Hotovo")
            msg.format_secondary_text("Konfigurace byla uložena a aplikována.")
            msg.run()
            msg.destroy()

        except subprocess.CalledProcessError:
            self.show_error("Nepodařilo se uložit systémovou konfiguraci (zamítnuto).")

    # --- Handlery Služeb ---
    def on_user_service_toggle(self, btn):
        action = "stop" if btn.get_label() == "Zastavit" else "start"
        subprocess.run(["systemctl", "--user", action, USER_SERVICE])
        self.refresh_services_only()

    def on_user_enable_toggle(self, switch, gparam):
        action = "enable" if switch.get_active() else "disable"
        subprocess.run(["systemctl", "--user", action, USER_SERVICE])
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
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK, text="Chyba")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    app = AsusSettingsApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
