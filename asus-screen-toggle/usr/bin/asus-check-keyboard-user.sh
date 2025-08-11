#!/bin/bash

if [[ -f /etc/asus-check-keyboard.cfg ]]; then
    source /etc/asus-check-keyboard.cfg
else
    exit 0
fi

if [[ -f /tmp/asus-rotation ]]; then
    source /tmp/asus-rotation
else
    exit 0
fi

echo "vid $VENDOR_ID"
echo "pid $PRODUCT_ID"
echo "pd $PRIMARY_DISPLAY_NAME"
echo "sd $SECONDARY_DISPLAY_NAME"
echo "lid $LID"

LID_STATE=$(grep -i "state" /proc/acpi/button/lid/${LID}/state | awk '{print $2}')
if [[ "$LID_STATE" == "closed" ]]; then
    echo "Víko je zavřené"
    exit 0
else
    echo "Víko je otevřené"
fi

if [ -z "$DIR" ]; then
    echo "DIR není nastavena nebo je prázdná"
    DIR=$(timeout 2 monitor-sensor --accel | grep orientation)
else
    echo "DIR $DIR"
fi
DISPLAY_ROTATION="normal"

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

user=$USER
sid=$XDG_SESSION_ID
runtime_dir=$XDG_RUNTIME_DIR
type=$XDG_SESSION_TYPE
desktop_env=$XDG_CURRENT_DESKTOP
session_name=$DESKTOP_SESSION
kde_session=$KDE_FULL_SESSION
gnome_session=$GNOME_DESKTOP_SESSION_ID

echo "👤 Uživatel: $user"
echo "   Sezení: $type"
echo "   Prostředí: $desktop_env ($session_name)"

if [[ "$user" == "sddm" ]]; then
    exit 0
fi

if [[ "$type" == "x11" ]]; then
    echo "🟢 Nalezen X11 uživatel: $user"
    echo "sid=$sid"
    echo "DISPLAY=$display"
    echo "XDG_RUNTIME_DIR=$runtime_dir"

    if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
        echo "Klávesnice detekována, vypínám spodní displej..."
        xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate normal --output ${SECONDARY_DISPLAY_NAME} --off
    else
        echo "Klávesnice není připojena, zapínám spodní displej..."
        # --- Výpočet nové pozice ---
        case "$DISPLAY_ROTATION" in
            *left*)
                xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION}
                ;;
            *right*)
                xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION}
                ;;
            *inverted*)
                xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION}
                ;;
            *normal*)
                xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION}
                ;;
            *)
                echo "Neplatná orientace: $DISPLAY_ROTATION"
                exit 1
                ;;
        esac
    fi
    exit 0
fi

if [[ "$type" == "wayland" && "$desktop_env" == "KDE" ]]; then
    echo "🟢 Nalezen KDE Wayland uživatel: $user"
    echo "sid=$sid"
    echo "WAYLAND_DISPLAY=$wayland"
    echo "XDG_RUNTIME_DIR=$runtime_dir"

    if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
        echo "Klávesnice detekována, vypínám spodní displej..."
        /usr/bin/kscreen-doctor output.${PRIMARY_DISPLAY_NAME}.rotation.normal
        /usr/bin/kscreen-doctor output.${SECONDARY_DISPLAY_NAME}.disable
    else
        echo "Klávesnice není připojena, zapínám spodní displej..."
        /usr/bin/kscreen-doctor output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
        /usr/bin/kscreen-doctor output.${SECONDARY_DISPLAY_NAME}.enable output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}

        # --- Získání geometrie primárního výstupu ---
        read PX PY PW PH <<< $(kscreen-doctor -o | awk -v out="$PRIMARY_DISPLAY_NAME" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')
        echo "$PRIMARY_DISPLAY_NAME $PX,$PY,$PW,$PH"

        # --- Získání velikosti sekundárního výstupu ---
        read SX SY SW SH <<< $(kscreen-doctor -o | awk -v out="$SECONDARY_DISPLAY_NAME" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')
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
        echo "Umísťuji $SECONDARY_DISPLAY_NAME $DISPLAY_ROTATION od $PRIMARY_DISPLAY_NAME na souřadnice $SX,$SY"
        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.position.$PX,$PY output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
        kscreen-doctor output.$SECONDARY_DISPLAY_NAME.position.$SX,$SY output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
    fi
    exit 0
fi

if [[ "$type" == "wayland" ]]; then
    echo "🟢 Nalezen Wayland uživatel: $user"
    echo "sid=$sid"
    echo "DISPLAY=$display"
    echo "XDG_RUNTIME_DIR=$runtime_dir"

    if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
        echo "Klávesnice detekována, vypínám spodní displej..."
        wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate normal
        wlr-randr --output ${SECONDARY_DISPLAY_NAME} --off
    else
        echo "Klávesnice není připojena, zapínám spodní displej..."
        wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION}

        # --- Výpočet nové pozice ---
        case "$DISPLAY_ROTATION" in
            *left*)
                wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME}
                ;;
            *right*)
                wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME}
                ;;
            *inverted*)
                wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME}
                ;;
            *normal*)
                wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME}
                ;;
            *)
                echo "Neplatná orientace: $DISPLAY_ROTATION"
                exit 1
                ;;
        esac
    fi
    exit 0
fi

exit 0
