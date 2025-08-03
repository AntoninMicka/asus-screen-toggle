#!/bin/bash

max_tries=1
delay=15
attempt=0

# Identifikace klávesnice (uprav podle potřeby)
VENDOR_ID="0B05"
PRODUCT_ID="1BF2"

# Výstupní jméno displeje (změň podle `kscreen-doctor -o`)
DISPLAY_NAME="eDP-2"

# while (( attempt < max_tries )); do
#     echo "⏳ Pokus $((attempt+1)) / $max_tries"

    sessions=$(loginctl list-sessions --no-legend | awk '{print $1}')
    for sid in $sessions; do
        user=$(loginctl show-session "$sid" -p Name --value)
        type=$(loginctl show-session "$sid" -p Type --value)

        if [[ "$type" == "x11" || "$user" == "sddm" ]]; then
            exit 0
        fi

        if [[ "$type" == "x11" || "$type" == "wayland" ]]; then
            USER_UID=$(loginctl show-session "$sid" -p User --value)
            runtime_dir=$(loginctl show-session "$sid" -p RuntimePath --value)
            runtime_dir="/run/user/$USER_UID"
            dbus_address="unix:path=$runtime_dir/bus"

            if [[ "$type" == "x11" ]]; then
                display=$(loginctl show-session "$sid" -p Display --value)
                xauth_file="/home/$user/.Xauthority"

                if [[ ! -f "$xauth_file" ]]; then
                    echo "⚠️  XAUTHORITY nenalezen pro uživatele $user. Přeskočeno."
                    continue
                fi

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

                if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
                    echo "Klávesnice detekována, vypínám spodní displej..."
                    sudo -u "$user" \
                        env DISPLAY="$display" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            XAUTHORITY="$xauth_file" \
                            xrandr --output ${DISPLAY_NAME} --off
                else
                    echo "Klávesnice není připojena, zapínám spodní displej..."
                    sudo -u "$user" \
                        env DISPLAY="$display" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            XAUTHORITY="$xauth_file" \
                            xrandr --output ${DISPLAY_NAME} --auto
                fi
            fi

            if [[ "$type" == "wayland" ]]; then
                wayland=$(loginctl show-session "$sid" -p WaylandDisplay --value)
                wayland=wayland-0
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
                if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
                    echo "Klávesnice detekována, vypínám spodní displej..."
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            /usr/bin/kscreen-doctor output.${DISPLAY_NAME}.disable
                else
                    echo "Klávesnice není připojena, zapínám spodní displej..."
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            /usr/bin/kscreen-doctor output.${DISPLAY_NAME}.enable
                fi
            fi

            exit 0  # Ukončit skript po prvním nalezeném GUI uživateli
        fi
    done

#     if [[  (attempt  + 1) < max_tries ]]; then
#         echo "❌ Žádný aktivní X11/Wayland uživatel. Čekám $delay s..."
#         (( attempt++ ))
#         sleep "$delay"
#     fi
# done

echo "❌ Nepodařilo se najít žádného uživatele v GUI po $max_tries pokusech."
exit 0
