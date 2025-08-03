#!/bin/bash

max_tries=5
delay=15
attempt=0

while (( attempt < max_tries )); do
    echo "⏳ Pokus $((attempt+1)) / $max_tries"

    sessions=$(loginctl list-sessions --no-legend | awk '{print $1}')
    for sid in $sessions; do
        user=$(loginctl show-session "$sid" -p Name --value)
        type=$(loginctl show-session "$sid" -p Type --value)

        if [[ "$type" == "x11" || "$type" == "wayland" ]]; then
            runtime_dir=$(loginctl show-session "$sid" -p RuntimePath --value)
            dbus_address="unix:path=$runtime_dir/bus"

            if [[ "$type" == "x11" ]]; then
                display=$(loginctl show-session "$sid" -p Display --value)

                echo "🟢 Nalezen X11 uživatel: $user"
                echo "sid=$sid"
                echo "DISPLAY=$display"
                echo "XDG_RUNTIME_DIR=$runtime_dir"

                # 💡 Tady můžeš dát X11-specifický příkaz
                #sudo -u "$user" \
                #    env DISPLAY="$display" \
                #         XDG_RUNTIME_DIR="$runtime_dir" \
                #         DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                #    notify-send "X11 sezení" "Uživatel $user je aktivní v X11"
            fi

            if [[ "$type" == "wayland" ]]; then
                wayland=$(loginctl show-session "$sid" -p WaylandDisplay --value)

                echo "🟢 Nalezen Wayland uživatel: $user"
                echo "sid=$sid"
                echo "WAYLAND_DISPLAY=$wayland"
                echo "XDG_RUNTIME_DIR=$runtime_dir"

                # 💡 Tady můžeš dát Wayland-specifický příkaz
                #sudo -u "$user" \
                #    env WAYLAND_DISPLAY="$wayland" \
                #         XDG_RUNTIME_DIR="$runtime_dir" \
                #         DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                #    notify-send "Wayland sezení" "Uživatel $user je aktivní ve Waylandu"
            fi

            exit 0  # Ukončit skript po prvním nalezeném GUI uživateli
        fi
    done

    echo "❌ Žádný aktivní X11/Wayland uživatel. Čekám $delay s..."
    (( attempt++ ))
    sleep "$delay"
done

echo "❌ Nepodařilo se najít žádného uživatele v GUI po $max_tries pokusech."
exit 0
