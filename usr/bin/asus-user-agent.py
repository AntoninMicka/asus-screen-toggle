#!/usr/bin/env python3
import sys
import os
import signal
import subprocess
import time
from pydbus import SessionBus
from gi.repository import GLib

# --- Konfigurace ---
BUS_NAME = "org.asus.ScreenToggle"
OBJECT_PATH = "/org/asus/ScreenToggle"
SCRIPT_PATH = "/usr/bin/asus-check-keyboard-user"
STATE_DIR = os.path.expanduser("~/.local/state/asus-check-keyboard")
STATE_FILE = os.path.join(STATE_DIR, "state")

class AsusScreenServer:
    """
    <node>
      <interface name="org.asus.ScreenToggle">
        <method name="Trigger"/>
        <method name="SetMode">
          <arg type="s" name="mode" direction="in"/>
        </method>
        <method name="Quit"/>
        <property name="Mode" type="s" access="read"/>
        <property name="KeyboardConnected" type="b" access="read"/>
      </interface>
    </node>
    """

    def __init__(self):
        self._mode = self._load_mode()
        self.last_file_mtime = 0
        if os.path.exists(STATE_FILE):
            self.last_file_mtime = os.stat(STATE_FILE).st_mtime

        # Sledování souboru (při změně z GUI)
        GLib.timeout_add_seconds(2, self._monitor_file_change)

    @property
    def Mode((self)):
        return self._mode

    @property
    def KeyboardConnected(self):
        result = subprocess.run([SCRIPT_PATH, "--keyboard-connected"], stdout=subprocess.DEVNULL)
        return result.returncode == 0

    def _load_mode(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return f.read().strip()
            except: pass
        return "automatic-enabled"

    def _save_mode(self, mode):
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            f.write(mode)
        self._mode = mode

    def _monitor_file_change(self):
        if os.path.exists(STATE_FILE):
            mtime = os.stat(STATE_FILE).st_mtime
            if mtime != self.last_file_mtime:
                self.last_file_mtime = mtime
                self._mode = self._load_mode()
                print(f"Server: Externí změna režimu na {self._mode}")
        return True

    def Trigger(self):
        subprocess.Popen([SCRIPT_PATH])
        return "OK"

    def SetMode(self, mode):
        self._save_mode(mode)
        subprocess.Popen([SCRIPT_PATH])
        return f"OK: {mode}"

    def Quit(self):
        loop.quit()

# --- Spuštění ---
if __name__ == "__main__":
    bus = SessionBus()
    server = AsusScreenServer()

    try:
        bus.publish(BUS_NAME, server)
        print(f"✅ Asus Screen Server běží na D-Bus: {BUS_NAME}")
    except Exception as e:
        print(f"❌ Start selhal: {e}")
        sys.exit(1)

    loop = GLib.MainLoop()

    # Signály pro čisté ukončení
    def stop_server(*args): loop.quit()
    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)

    loop.run()
