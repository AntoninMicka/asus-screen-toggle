#!/usr/bin/env python3
import sys
import os
import subprocess
import gi
import gettext
import locale
import shutil

# --- LOCALIZATION ---
APP_NAME = "asus-screen-toggle"
LOCALE_DIR = "/usr/share/locale"

try:
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
    gettext.textdomain(APP_NAME)
    _ = gettext.gettext
except Exception as e:
    _ = lambda s: s

try:
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib, GdkPixbuf
except ValueError:
    print(_("Error: Gtk 3.0 not found."))
    sys.exit(1)

try:
    from pydbus import SessionBus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    print(_("Warning: pydbus not found. Direct D-Bus communication disabled."))

# --- CONSTANTS ---
APP_TITLE = _("Asus Screen Toggle Settings")
BUS_NAME = "org.asus.ScreenToggle"
USER_SERVICE = "asus-screen-toggle.service"
SYSTEM_SERVICE = "asus-bottom-screen-init.service"
SYSTRAY_SERVICE = "asus-user-agent.service"

SYSTEM_CONFIG_FILE = "/etc/asus-screen-toggle.conf"
USER_CONFIG_FILE = os.path.expanduser("~/.config/asus-screen-toggle/user.conf")
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")
ICON_PATH = "/usr/share/asus-screen-toggle"

class AsusSettingsApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_border_width(10)
        self.set_default_size(650, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.icon_map = {
            "automatic-enabled": "icon-green.svg",
            "automatic-disabled": "icon-red.svg",
            "enforce-desktop": "icon-blue.svg",
            "temp-desktop": "icon-yellow.svg",
            "temp-mirror": "icon-yellow.svg",
            "temp-reverse-mirror": "icon-yellow.svg",
            "temp-rotated-desktop": "icon-yellow.svg",
            "temp-primary-only": "icon-yellow.svg",
            "temp-secondary-only": "icon-yellow.svg"
        }

        self.temporary_actions = []
        self.current_mode_in_ui = None

        # Main Layout
        main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_layout)

        self.notebook = Gtk.Notebook()
        main_layout.pack_start(self.notebook, True, True, 0)

        # Tabs
        self._setup_home_tab()
        self._setup_general_tab()
        self._setup_hardware_tab()

        # Action Buttons
        bbox = Gtk.ButtonBox(layout_style=Gtk.ButtonBoxStyle.END)
        main_layout.pack_end(bbox, False, False, 0)

        btn_refresh = Gtk.Button(label=_("Refresh"))
        btn_refresh.connect("clicked", lambda x: self.refresh_all())
        bbox.add(btn_refresh)

        btn_save = Gtk.Button(label=_("Save All"))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        bbox.add(btn_save)

        self.refresh_all()
        GLib.timeout_add_seconds(3, self.refresh_services_only)

    def _setup_home_tab(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_border_width(20)
        self.notebook.append_page(page, Gtk.Label(label=_("Home")))

        lbl_welcome = Gtk.Label(label=_("<span size='x-large' weight='bold'>Quick Control</span>"))
        lbl_welcome.set_use_markup(True)
        page.pack_start(lbl_welcome, False, False, 10)

        hbox_modes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hbox_modes.set_halign(Gtk.Align.CENTER)
        page.pack_start(hbox_modes, False, False, 0)

        self.btn_mode_auto = self.create_mode_button(_("Automatic"), "icon-green.svg", _("Sensor-based"), "automatic-enabled")
        self.btn_mode_primary = self.create_mode_button(_("Primary Only"), "icon-red.svg", _("Always disabled"), "automatic-disabled")
        self.btn_mode_desktop = self.create_mode_button(_("Both Displays"), "icon-blue.svg", _("Force extended"), "enforce-desktop")

        hbox_modes.pack_start(self.btn_mode_auto, True, True, 0)
        hbox_modes.pack_start(self.btn_mode_primary, True, True, 0)
        hbox_modes.pack_start(self.btn_mode_desktop, True, True, 0)

        page.pack_start(Gtk.Separator(), False, False, 10)

        lbl_tmp = Gtk.Label(label=_("<span size='large' weight='bold'>Presentation Modes</span>\n"
                                    "<i>Resets when keyboard is attached.</i>"))
        lbl_tmp.set_use_markup(True)
        lbl_tmp.set_justify(Gtk.Justification.CENTER)
        page.pack_start(lbl_tmp, False, False, 0)

        grid_tmp = Gtk.Grid()
        grid_tmp.set_column_spacing(15)
        grid_tmp.set_row_spacing(15)
        grid_tmp.set_halign(Gtk.Align.CENTER)
        page.pack_start(grid_tmp, True, True, 0)

        tmp_list = [
            (_("Mirror"), "temp-mirror", 0, 0),
            (_("Reverse"), "temp-reverse-mirror", 1, 0),
            (_("Rotated"), "temp-rotated-desktop", 2, 0),
            (_("Desktop"), "temp-desktop", 0, 1),
            (_("Off Sec."), "temp-primary-only", 1, 1),
            (_("Off Main"), "temp-secondary-only", 2, 1),
        ]

        for label, mid, col, row in tmp_list:
            btn = self.create_mode_button(label, "icon-yellow.svg", "", mid)
            btn.set_size_request(120, 90)
            grid_tmp.attach(btn, col, row, 1, 1)
            self.temporary_actions.append(btn)

        btn_check = Gtk.Button(label=_("🔄 Run check now"))
        btn_check.set_halign(Gtk.Align.CENTER)
        btn_check.connect("clicked", lambda x: self.run_check())
        page.pack_start(btn_check, False, False, 10)

    def _setup_general_tab(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        self.notebook.append_page(page, Gtk.Label(label=_("Services")))

        frame = Gtk.Frame(label=_("Service Status"))
        page.pack_start(frame, False, False, 0)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_border_width(10)
        frame.add(vbox)

        self.status_user = Gtk.Label(label="...")
        self.btn_user_toggle = Gtk.Button(label="...")
        self.btn_user_toggle.connect("clicked", self.on_user_service_toggle)
        self.switch_user_enable = Gtk.Switch()
        vbox.pack_start(self.create_service_row(_("User Agent"), self.status_user, self.btn_user_toggle, self.switch_user_enable), False, False, 0)

        self.status_systray = Gtk.Label(label="...")
        self.btn_systray_toggle = Gtk.Button(label="...")
        self.btn_systray_toggle.connect("clicked", self.on_systray_service_toggle)
        self.switch_systray_enable = Gtk.Switch()
        vbox.pack_start(self.create_service_row(_("Status Indicator"), self.status_systray, self.btn_systray_toggle, self.switch_systray_enable), False, False, 0)

        frame_user = Gtk.Frame(label=_("User Configuration"))
        page.pack_start(frame_user, False, False, 0)
        vbox_user = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox_user.set_border_width(10)
        frame_user.add(vbox_user)

        self.user_chk_dbus = Gtk.CheckButton(label=_("Enable D-Bus Control"))
        self.user_chk_signal = Gtk.CheckButton(label=_("Enable Signal/Rotation Handling"))
        vbox_user.pack_start(self.user_chk_dbus, False, False, 0)
        vbox_user.pack_start(self.user_chk_signal, False, False, 0)

    def _setup_hardware_tab(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        self.notebook.append_page(page, Gtk.Label(label=_("Hardware")))

        self.sys_chk_direct = Gtk.CheckButton(label=_("Enable Direct Call (Udev)"))
        self.sys_chk_dbus = Gtk.CheckButton(label=_("Enable D-Bus (System)"))
        self.sys_chk_signal = Gtk.CheckButton(label=_("Enable Signal (System)"))
        self.sys_chk_systemd = Gtk.CheckButton(label=_("Enable Systemd Call"))
        page.pack_start(self.sys_chk_dbus, False, False, 0)
        page.pack_start(self.sys_chk_signal, False, False, 0)
        page.pack_start(self.sys_chk_direct, False, False, 0)
        page.pack_start(self.sys_chk_systemd, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        page.pack_start(grid, False, False, 10)

        self.entry_vendor = Gtk.Entry()
        self.entry_product = Gtk.Entry()
        self.entry_primary = Gtk.Entry()
        self.entry_secondary = Gtk.Entry()
        self.entry_lid = Gtk.Entry()

        self.add_config_row(grid, 0, _("Vendor ID:"), self.entry_vendor, "0b05")
        self.add_config_row(grid, 1, _("Product ID:"), self.entry_product, "1bf2")
        self.add_config_row(grid, 2, _("Primary Display:"), self.entry_primary, "eDP-1")
        self.add_config_row(grid, 3, _("Secondary Display:"), self.entry_secondary, "eDP-2")
        self.add_config_row(grid, 4, _("Lid Sensor:"), self.entry_lid, "LID")

    # --- CORE LOGIC ---

    def on_mode_clicked(self, btn):
        mode = btn.mode_id
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                f.write(mode)

            if DBUS_AVAILABLE:
                try:
                    bus = SessionBus()
                    proxy = bus.get(BUS_NAME)
                    proxy.SetMode(mode)
                except:
                    self.run_check()
            else:
                self.run_check()

            self.update_home_ui_state(mode)
        except Exception as e:
            self.show_error(f"Error: {e}")

    def on_save_clicked(self, widget):
        # User Config
        try:
            os.makedirs(os.path.dirname(USER_CONFIG_FILE), exist_ok=True)
            with open(USER_CONFIG_FILE, 'w') as f:
                f.write(f"ENABLE_DBUS={'true' if self.user_chk_dbus.get_active() else 'false'}\n")
                f.write(f"ENABLE_SIGNAL={'true' if self.user_chk_signal.get_active() else 'false'}\n")
        except Exception as e:
            self.show_error(f"User config save failed: {e}")

        # System Config (requires pkexec)
        sys_content = f"""VENDOR_ID="{self.entry_vendor.get_text()}"
PRODUCT_ID="{self.entry_product.get_text()}"
PRIMARY_DISPLAY_NAME="{self.entry_primary.get_text()}"
SECONDARY_DISPLAY_NAME="{self.entry_secondary.get_text()}"
LID="{self.entry_lid.get_text()}"
ENABLE_DIRECT_CALL={'true' if self.sys_chk_direct.get_active() else 'false'}
ENABLE_DBUS={'true' if self.sys_chk_dbus.get_active() else 'false'}
ENABLE_SIGNAL={'true' if self.sys_chk_signal.get_active() else 'false'}
ENABLE_SYSTEMD_CALL={'true' if self.sys_chk_systemd.get_active() else 'false'}
"""
        cmd = f"cat <<EOF > /tmp/asus_conf_tmp\n{sys_content}EOF\npkexec mv /tmp/asus_conf_tmp {SYSTEM_CONFIG_FILE}"
        subprocess.run(["bash", "-c", cmd])
        self.refresh_all()

    def refresh_all(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    mode = f.read().strip()
                    self.update_home_ui_state(mode)
            except: pass
        self.load_configs()
        self.refresh_services_only()

    def load_configs(self):
        # Placeholder for your config parsing logic (parse /etc and ~/.config)
        pass

    def run_check(self):
        subprocess.Popen(["asus-check-keyboard-user"])

    def is_keyboard_connected(self):
        res = subprocess.run(["asus-check-keyboard-user", "--keyboard-connected"], stdout=subprocess.DEVNULL)
        return res.returncode == 0

    # --- UI HELPERS ---

    def update_home_ui_state(self, current_mode):
        kb_connected = self.is_keyboard_connected()
        self.current_mode_in_ui = current_mode

        def process(widget):
            if isinstance(widget, Gtk.Button) and hasattr(widget, "mode_id"):
                is_active = (widget.mode_id == current_mode)
                widget.set_sensitive(not is_active)
                if widget.mode_id.startswith("temp-") and kb_connected:
                    widget.set_sensitive(False)
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children(): process(child)

        process(self)
        self.update_window_icon(current_mode)

    def create_mode_button(self, title, icon_file, subtitle, mode_id):
        btn = Gtk.Button()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        icon_path = os.path.join(ICON_PATH, icon_file)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 48, 48, True)
            img = Gtk.Image.new_from_pixbuf(pixbuf)
        except:
            img = Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        vbox.pack_start(img, True, True, 5)
        lbl_title = Gtk.Label(label=f"<b>{title}</b>")
        lbl_title.set_use_markup(True)
        vbox.pack_start(lbl_title, False, False, 0)
        if subtitle:
            lbl_sub = Gtk.Label(label=f"<small>{subtitle}</small>")
            lbl_sub.set_use_markup(True)
            vbox.pack_start(lbl_sub, False, False, 0)
        btn.add(vbox)
        btn.mode_id = mode_id
        btn.connect("clicked", self.on_mode_clicked)
        return btn

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

    def update_window_icon(self, mode):
        icon_name = self.icon_map.get(mode, "icon-green.svg")
        icon_path = os.path.join(ICON_PATH, icon_name)
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

    def refresh_services_only(self):
        # Add your service status update logic here
        return True

    def show_error(self, message):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=_("Error"))
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    # Stub handlers for services
    def on_user_service_toggle(self, btn): pass
    def on_systray_service_toggle(self, btn): pass

if __name__ == "__main__":
    app = AsusSettingsApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
