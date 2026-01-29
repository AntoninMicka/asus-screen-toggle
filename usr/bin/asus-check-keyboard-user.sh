#!/bin/bash

export TEXTDOMAIN="asus-screen-toggle"
export TEXTDOMAINDIR="/usr/share/locale"

# Funkce pro zjednodušení (alias)
function _() {
    gettext "$1"
}

# --- 1. Načtení konfigurace ---
if [[ -f /etc/asus-screen-toggle.conf ]]; then
    source /etc/asus-screen-toggle.conf
else
    VENDOR_ID="0b05"
    PRODUCT_ID="1bf2"
    PRIMARY_DISPLAY_NAME="eDP-1"
    SECONDARY_DISPLAY_NAME="eDP-2"
fi

# Rychlá kontrola pro volání z agenta
if [[ "$1" == "--keyboard-connected" ]]; then
    if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
        exit 0   # true
    else
        exit 1   # false
    fi
fi

# Detekce orientace ze senzoru
if [[ -f /tmp/asus-rotation ]]; then
    source /tmp/asus-rotation
else
    DIR=$(timeout 0.5 monitor-sensor --accel | grep -m 1 orientation | cut -d: -f2 | xargs)
fi

# --- 2. Zjištění požadavku uživatele (State) ---
APP_NAME="asus-check-keyboard"
STATE_FILE="$HOME/.local/state/$APP_NAME/state"
USER_STATE="automatic-enabled"

if [[ -f "$STATE_FILE" ]]; then
    USER_STATE=$(<"$STATE_FILE")
fi

# --- 3. Rozhodovací logika (Matrix) ---
FORCE_MIRROR=false
FORCE_REVERSE=false
ENABLE_PRIMARY_SCREEN=true
ENABLE_BOTTOM_SCREEN=true
DISABLE_ROTATION=false

# A) Fyzická kontrola klávesnice
PHYSICAL_KEYBOARD_CONNECTED=false
if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
    PHYSICAL_KEYBOARD_CONNECTED=true
    DISABLE_ROTATION=true
    ENABLE_BOTTOM_SCREEN=false
    echo "$(_ "Fyzická klávesnice: PŘIPOJENA")"
else
    echo "$(_ "Fyzická klávesnice: ODPOJENA")"
fi

# Automatický návrat z dočasných režimů při zaklapnutí klávesnice
if [[ "$PHYSICAL_KEYBOARD_CONNECTED" == "true" && "$USER_STATE" == temp-* ]]; then
    echo "$(_ "Klávesnice připojena → návrat do preferovaného režimu")"
    USER_STATE=$(grep "PREFERRED_MODE" "$HOME/.config/asus-screen-toggle/user.conf" | cut -d'=' -f2 || echo "automatic-enabled")
    echo "$USER_STATE" > "$STATE_FILE"
fi

# B) Aplikace sady osmi režimů
case "$USER_STATE" in
    automatic-disabled)
        ENABLE_BOTTOM_SCREEN=false
        DISABLE_ROTATION=true
        ;;
    automatic-enabled)
        # Výchozí stav (nastaven v bodě A)
        ;;
    temp-desktop | enforce-desktop)
        ENABLE_BOTTOM_SCREEN=true
        ;;
    temp-mirror)
        ENABLE_BOTTOM_SCREEN=true
        FORCE_MIRROR=true
        ;;
    temp-reverse-mirror)
        ENABLE_BOTTOM_SCREEN=true
        FORCE_MIRROR=true
        FORCE_REVERSE=true
        DISABLE_ROTATION=true
        ;;
    temp-rotated-desktop)
        ENABLE_BOTTOM_SCREEN=true
        FORCE_REVERSE=true
        DISABLE_ROTATION=true
        ;;
    temp-primary-only)
        ENABLE_BOTTOM_SCREEN=false
        ;;
    temp-secondary-only)
        ENABLE_BOTTOM_SCREEN=true
        ENABLE_PRIMARY_SCREEN=false
        ;;
esac

# --- 4. Příprava proměnných pro rotaci ---
DISPLAY_ROTATION="normal"
PRIMARY_DISPLAY_ROTATION="normal"
SECONDARY_DISPLAY_ROTATION="normal"

if [[ "$DISABLE_ROTATION" == "true" || "$FORCE_REVERSE" == "true" ]]; then
    if [[ "$FORCE_REVERSE" == "true" ]]; then
        PRIMARY_DISPLAY_ROTATION="inverted"
        SECONDARY_DISPLAY_ROTATION="normal"
    fi
else
    case "$DIR" in
        *normal*)    DISPLAY_ROTATION="normal"   ;;
        *bottom-up*) DISPLAY_ROTATION="inverted" ;;
        *left-up*)   DISPLAY_ROTATION="left"     ;;
        *right-up*)  DISPLAY_ROTATION="right"    ;;
    esac
    PRIMARY_DISPLAY_ROTATION=$DISPLAY_ROTATION
    SECONDARY_DISPLAY_ROTATION=$DISPLAY_ROTATION
fi

# --- 5. Aplikace nastavení ---
user=$USER
type=$XDG_SESSION_TYPE
desktop_env=$XDG_CURRENT_DESKTOP

if [[ "$user" == "sddm" ]]; then exit 0; fi

# === X11 ===
if [[ "$type" == "x11" ]]; then
    if [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "true" && "$FORCE_MIRROR" == "true" ]]; then
        xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --auto \
               --output ${SECONDARY_DISPLAY_NAME} --rotate ${SECONDARY_DISPLAY_ROTATION} --auto --same-as ${PRIMARY_DISPLAY_NAME}
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --auto --output ${SECONDARY_DISPLAY_NAME} --off
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "false" && "$ENABLE_BOTTOM_SCREEN" == "true" ]]; then
        xrandr --output ${PRIMARY_DISPLAY_NAME} --off --output ${SECONDARY_DISPLAY_NAME} --rotate ${SECONDARY_DISPLAY_ROTATION} --auto
    else
        case "$DISPLAY_ROTATION" in
            *left*)   xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME} --auto --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} ;;
            *right*)  xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME}  --auto --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} ;;
            *inverted*) xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME} --auto --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} ;;
            *)        xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${PRIMARY_DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME}  --auto --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} ;;
        esac
    fi
    exit 0
fi

# === Wayland (KDE) ===
if [[ "$type" == "wayland" && "$desktop_env" == "KDE" ]]; then
    if [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "true" && "$FORCE_MIRROR" == "true" ]]; then
        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.enable output.$PRIMARY_DISPLAY_NAME.position.0,0 output.${PRIMARY_DISPLAY_NAME}.rotation.${PRIMARY_DISPLAY_ROTATION} \
                       output.${SECONDARY_DISPLAY_NAME}.enable output.$SECONDARY_DISPLAY_NAME.position.0,0 output.${SECONDARY_DISPLAY_NAME}.rotation.${SECONDARY_DISPLAY_ROTATION}
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.enable output.${PRIMARY_DISPLAY_NAME}.rotation.${PRIMARY_DISPLAY_ROTATION} output.${SECONDARY_DISPLAY_NAME}.disable
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "false" && "$ENABLE_BOTTOM_SCREEN" == "true" ]]; then
        kscreen-doctor output.${PRIMARY_DISPLAY_NAME}.disable output.$SECONDARY_DISPLAY_NAME.enable output.${SECONDARY_DISPLAY_NAME}.rotation.${SECONDARY_DISPLAY_ROTATION}
    else
        # Dual Screen / Rotated Desktop logic
        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.enable output.${PRIMARY_DISPLAY_NAME}.rotation.${PRIMARY_DISPLAY_ROTATION} \
                       output.${SECONDARY_DISPLAY_NAME}.enable output.${SECONDARY_DISPLAY_NAME}.rotation.${SECONDARY_DISPLAY_ROTATION}

        # Získání geometrie primárního výstupu
        read PX PY PW PH <<< $(kscreen-doctor -o | awk -v out="$PRIMARY_DISPLAY_NAME" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')
        # Získání velikosti sekundárního výstupu
        read SX SY SW SH <<< $(kscreen-doctor -o | awk -v out="$SECONDARY_DISPLAY_NAME" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }')

        PX=0; PY=0
        case "$DISPLAY_ROTATION" in
            *left*)     SX=$((PX - SW)); SY=$PY ;;
            *right*)    SX=$((PX + PW)); SY=$PY ;;
            *inverted*) SX=$PX; SY=$((PY - SH)) ;;
            *)          SX=$PX; SY=$((PY + PH)) ;;
        esac
        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.position.$PX,$PY output.${PRIMARY_DISPLAY_NAME}.rotation.${PRIMARY_DISPLAY_ROTATION} \
                       output.$SECONDARY_DISPLAY_NAME.position.$SX,$SY output.${SECONDARY_DISPLAY_NAME}.rotation.${SECONDARY_DISPLAY_ROTATION}
    fi
    exit 0
fi

# === Wayland (Generic / wlroots) ===
if [[ "$type" == "wayland" ]]; then
    if [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "true" && "$FORCE_MIRROR" == "true" ]]; then
        wlr-randr --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} \
                  --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} --same-as ${PRIMARY_DISPLAY_NAME}
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "true" && "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        wlr-randr --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} --output ${SECONDARY_DISPLAY_NAME} --off
    elif [[ "$ENABLE_PRIMARY_SCREEN" == "false" && "$ENABLE_BOTTOM_SCREEN" == "true" ]]; then
        wlr-randr --output ${PRIMARY_DISPLAY_NAME} --off --output ${SECONDARY_DISPLAY_NAME} --rotate ${SECONDARY_DISPLAY_ROTATION} --auto
    else
        case "$DISPLAY_ROTATION" in
            *left*)   wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME} ;;
            *right*)  wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME} ;;
            *inverted*) wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME} ;;
            *)        wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${SECONDARY_DISPLAY_ROTATION} --output ${PRIMARY_DISPLAY_NAME} --auto --rotate ${PRIMARY_DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME} ;;
        esac
    fi
    exit 0
fi
