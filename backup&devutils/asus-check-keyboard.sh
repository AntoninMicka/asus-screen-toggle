#!/bin/bash

max_tries=1
delay=15
attempt=0

# Identifikace klávesnice (uprav podle potřeby)
VENDOR_ID="0B05"
PRODUCT_ID="1BF2"

# Výstupní jméno displeje (změň podle `kscreen-doctor -o`)
PRIMARY_DISPLAY_NAME="eDP-1"
SECONDARY_DISPLAY_NAME="eDP-2"

DIR=$(timeout 2 monitor-sensor --accel | grep orientation)
DISPLAY_ROTATION="normal"

KSCREEN_BIN=$(command -v kscreen-doctor || echo "/usr/bin/kscreen-doctor")

case "$DIR" in
*normal*)
    DISPLAY_ROTATION="normal"
    echo "qdbus org.kde.KWin /KWin setScreenRotation 0"
    ;;
*bottom-up*)
    DISPLAY_ROTATION="inverted"
    echo "qdbus org.kde.KWin /KWin setScreenRotation 180"
    ;;
*left-up*)
    DISPLAY_ROTATION="left"
    echo "qdbus org.kde.KWin /KWin setScreenRotation 270"
    ;;
*right-up*)
    DISPLAY_ROTATION="right"
    echo "qdbus org.kde.KWin /KWin setScreenRotation 90"
    ;;
esac

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
                            xrandr --output ${SECONDARY_DISPLAY_NAME} --off
                else
                    echo "Klávesnice není připojena, zapínám spodní displej..."
                    sudo -u "$user" \
                        env DISPLAY="$display" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            XAUTHORITY="$xauth_file" \
                            xrandr --output ${SECONDARY_DISPLAY_NAME} --auto
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
                sudo -u "$user" \
                    env WAYLAND_DISPLAY="$wayland" \
                        XDG_RUNTIME_DIR="$runtime_dir" \
                        DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                        $KSCREEN_BIN output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}

                if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
                    echo "Klávesnice detekována, vypínám spodní displej..."
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            $KSCREEN_BIN output.${SECONDARY_DISPLAY_NAME}.disable
                else
                    echo "Klávesnice není připojena, zapínám spodní displej..."
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            $KSCREEN_BIN output.${SECONDARY_DISPLAY_NAME}.enable output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
                    # --- Získání geometrie primárního výstupu ---
                    read PX PY PW PH <<< $(
                        sudo -u "$user" \
                            env WAYLAND_DISPLAY="$wayland" \
                                XDG_RUNTIME_DIR="$runtime_dir" \
                                DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                                kscreen-doctor -o | awk -v out="$output" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')
                        echo "$PRIMARY_DISPLAY_NAME $PX,$PY,$PW,$PH"

                    # --- Získání velikosti sekundárního výstupu ---
                    read SX SY SW SH <<< $(
                        sudo -u "$user" \
                            env WAYLAND_DISPLAY="$wayland" \
                                XDG_RUNTIME_DIR="$runtime_dir" \
                                DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                                kscreen-doctor -o | awk -v out="$output" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')
                    echo "$SECONDARY_DISPLAY_NAME $SX,$SY,$SW,$SH"

                    PX=0
                    PY=0

                    # --- Výpočet nové pozice ---
                    case "$DISPLAY_ROTATION" in
                        *left*)
                            PX=$(echo "$PX" | tr -dc '0-9')
                            SW=$(echo "$SW" | tr -dc '0-9')
                            SX=$((PX - SW))
                            SY=$PY
                            ;;
                        *right*)
                            PX=$(echo "$PX" | tr -dc '0-9')
                            PW=$(echo "$PW" | tr -dc '0-9')
                            SX=$((PX + PW))
                            SY=$PY
                            ;;
                        *inverted*)
                            SX=$PX
                            SY=$((PY - SH))
                            ;;
                        *normal*)
                            SX=$PX
                            SY=$((PY + PH))
                            ;;
                        *)
                            echo "Neplatná orientace: $DISPLAY_ROTATION"
                            exit 1
                            ;;
                    esac

                    echo "$PRIMARY_DISPLAY_NAME $PX,$PY,$PW,$PH"
                    echo "$SECONDARY_DISPLAY_NAME $SX,$SY,$SW,$SH"

                    # --- Výstup a nastavení ---
                    echo "Umísťuji $SECONDARY_DISPLAY_NAME $DISPLAY_ROTATIONod $PRIMARY_DISPLAY_NAME na souřadnice $SX,$SY"
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            $KSCREEN_BIN output.$PRIMARY_DISPLAY_NAME.position.$PX,$PY output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
                    sudo -u "$user" \
                        env WAYLAND_DISPLAY="$wayland" \
                            XDG_RUNTIME_DIR="$runtime_dir" \
                            DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
                            $KSCREEN_BIN output.$SECONDARY_DISPLAY_NAME.position.$SX,$SY output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
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
