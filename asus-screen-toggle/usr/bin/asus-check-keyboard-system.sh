#!/bin/bash

LOCKFILE="/run/asus-bottom-screen-init.lock"
exec 9>"$LOCKFILE" || exit 0
flock -n 9 || exit 0

REASON="${1:-UNKNOWN}"

case "$REASON" in
  USB_ADD|USB_REMOVE)
    # tady klidně BEZ delaye
    ;;
  DRM_CHANGE)
    # DRM debounce
    sleep 0.5
    ;;
  *)
    ;;
esac

max_tries=1
delay=15
attempt=0

ENABLE_DIRECT_CALL="false"
ENABLE_DBUS="false"
ENABLE_SIGNAL="false"
ENABLE_SYSTEMD_CALL="true"

USER_BIN=$(command -v asus-check-keyboard-user || echo "/usr/bin/asus-check-keyboard-user")

# --- 1. Načtení konfigurace ---
if [[ -f /etc/asus-screen-toggle.conf ]]; then
    source /etc/asus-screen-toggle.conf
else
    exit 0
fi
# while (( attempt < max_tries )); do
#     echo "⏳ Pokus $((attempt+1)) / $max_tries"

    sessions=$(loginctl list-sessions --no-legend | awk '{print $1}')
    for sid in $sessions; do
        user=$(loginctl show-session "$sid" -p Name --value)
        type=$(loginctl show-session "$sid" -p Type --value)
        desktop=$(loginctl show-session "$sid" -p Desktop --value)
        state=$(loginctl show-session "$sid" -p State --value)

        # Pokud sezení není aktivní, přeskočíme ho
        if [[ "$state" != "active" ]]; then
            echo "⚪ Sezení $sid (uživatel $user) není aktivní (stav: $state). Přeskakuji."
            continue
        fi

        if [[ "$user" == "sddm" || "$user" == "gdm" || "$user" == "lightdm" ]]; then
            continue
        fi

        if [[ "$type" == "x11" || "$type" == "wayland" ]]; then

            # --- PŘÍPRAVA PROMĚNNÝCH PRO KOMUNIKACI ---
            USER_UID=$(loginctl show-session "$sid" -p User --value)

            # Zkusíme získat runtime cestu dynamicky, fallback na standardní cestu
            runtime_path=$(loginctl show-session "$sid" -p RuntimePath --value)
            if [[ -z "$runtime_path" ]]; then
                runtime_path="/run/user/$USER_UID"
            fi

            if [[ "$ENABLE_SYSTEMD_CALL" == "true" ]]; then
                if systemctl --user --machine="$USER_UID@.host" start asus-screen-toggle.service > /dev/null 2>&1; then
                #if systemctl --user --machine="$USER_UID@.host" reload asus-screen-toggle.service > /dev/null 2>&1; \
                #|| systemctl --user --machine="$USER_UID@.host" restart asus-screen-toggle.service > /dev/null 2>&1; then

                    echo "✅ Systemd: Zpráva úspěšně odeslána agentovi."
                    exit 0
                fi
            fi

            # Adresa sběrnice je klíčová pro D-Bus volání
            dbus_address="unix:path=$runtime_path/bus"

            echo "🔎 Kontrola uživatele $user (UID: $USER_UID, SID: $sid, Type: $type)"


            # --- 1. MOŽNOST: D-BUS VOLÁNÍ (Python Agent) ---
            # Pokusíme se zavolat metodu Trigger na novém Python agentovi.
            # Timeout nastavíme krátký (1s), aby to nezdržovalo, pokud agent neběží.
            # Přesměrujeme stderr, abychom nešpinili logy, pokud služba neexistuje.

            if [[ "$ENABLE_DBUS" == "true" ]]; then
                if sudo -u "$user" DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                dbus-send --session --print-reply --reply-timeout=1000 --dest=org.asus.ScreenToggle \
                /org/asus/ScreenToggle org.asus.ScreenToggle.Trigger > /dev/null 2>&1; then

                    echo "✅ D-Bus: Zpráva úspěšně odeslána agentovi."
                    exit 0
                fi
            fi


            # --- 2. MOŽNOST: SIGNÁL (Legacy Shell Agent) ---
            # Pokud D-Bus selhal (agent neběží nebo je to stará verze), zkusíme najít PID.
            # Hledáme primárně starý shell skript. Nový python skript už by měl zareagovat na D-Bus výše,
            # ale pro jistotu můžeme signál poslat i jemu, pokud by visel na D-Busu.

            if [[ "$ENABLE_SIGNAL" == "true" ]]; then
                AGENT_PID=$(pgrep -u "$user" -f "asus-user-agent" | head -n 1)

                # Pokud nenajdeme shell skript, zkusíme najít python proces (fallback pro signál)
                if [[ -z "$AGENT_PID" ]]; then
                    AGENT_PID=$(pgrep -u "$user" -f "asus-user-agent" | head -n 1)
                fi

                if [[ -n "$AGENT_PID" ]]; then
                    echo "🟢 Nalezen běžící agent (PID $AGENT_PID). Posílám signál SIGUSR1."
                    kill -SIGUSR1 "$AGENT_PID"
                    exit 0
                fi
            fi


            if [[ "$ENABLE_DIRECT_CALL" == "true" ]]; then
            # --- 3. MOŽNOST: PŘÍMÉ VOLÁNÍ (Fallback bez agenta) ---
                echo "⚠️ Žádný agent neodpověděl. Používám přímé volání přes sudo."

                # Pro X11 potřebujeme DISPLAY a Xauthority
                if [[ "$type" == "x11" ]]; then
                    display=$(loginctl show-session "$sid" -p Display --value)
                    xauth_file="/home/$user/.Xauthority"

                    if [[ ! -f "$xauth_file" ]]; then
                        echo "⚠️  XAUTHORITY nenalezen pro uživatele $user. Přeskočeno."
                        continue
                    fi

                    sudo -u "$user" \
                        env DISPLAY="$display" \
                            XDG_SESSION_ID="$sid" \
                            XDG_SESSION_TYPE="$type" \
                            XDG_CURRENT_DESKTOP="$desktop" \
                            XDG_RUNTIME_DIR="$runtime_path" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            DIR="$DIR" \
                        $USER_BIN
                fi

                # Pro Wayland potřebujeme WAYLAND_DISPLAY
                if [[ "$type" == "wayland" ]]; then
                    # Někdy loginctl nevrátí WaylandDisplay, zkusíme default
                    wayland_disp=$(loginctl show-session "$sid" -p WaylandDisplay --value)
                    if [[ -z "$wayland_disp" ]]; then
                        wayland_disp="wayland-0"
                    fi

                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland_disp" \
                            XDG_SESSION_ID="$sid" \
                            XDG_SESSION_TYPE="$type" \
                            XDG_CURRENT_DESKTOP="$desktop" \
                            XDG_RUNTIME_DIR="$runtime_path" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            DIR="$DIR" \
                        $USER_BIN
                fi
            fi

            exit 0  # Ukončit skript po prvním nalezeném a obslouženém uživateli
        fi
    done

#     if [[  (attempt  + 1) < max_tries ]]; then
#         ...
#     fi
# done

echo "❌ Nepodařilo se najít žádného uživatele v GUI po $max_tries pokusech."
exit 0
