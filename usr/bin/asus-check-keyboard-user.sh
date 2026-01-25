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
    # Pokud konfig neexistuje, nastavíme defaulty, aby skript nespadl
    VENDOR_ID="0b05"
    PRODUCT_ID="1bf2"
    PRIMARY_DISPLAY_NAME="eDP-1"
    SECONDARY_DISPLAY_NAME="eDP-2"
fi

# Pokud máme rotaci z monitor-sensor (uloženou v tmp), načteme ji
if [[ -f /tmp/asus-rotation ]]; then
    source /tmp/asus-rotation
else
    # Fallback, pokud neexistuje temp soubor (např. ruční spuštění)
    # timeout zajistí, že se nezasekne, pokud senzor není dostupný
    DIR=$(timeout 0.5 monitor-sensor --accel | grep -m 1 orientation)
fi

# --- 2. Zjištění požadavku uživatele (State) ---
APP_NAME="asus-check-keyboard"
STATE_FILE="$HOME/.local/state/$APP_NAME/state"
USER_STATE="automatic-enabled"

if [[ -f "$STATE_FILE" ]]; then
    USER_STATE=$(<"$STATE_FILE")
fi

printf "$(_ "VID: %s, PID: %s")\n" "$VENDOR_ID" "$PRODUCT_ID"
printf "$(_ "User mode: %s")\n" "$USER_STATE"
printf "$(_ "Sensor: %s")\n" "$DIR"

# --- 3. Rozhodovací logika (Matrix) ---

FORCE_MIRROR=false
FORCE_REVERSE=false
DISABLE_ROTATION=false

# A) Je fyzicky připojená klávesnice?
PHYSICAL_KEYBOARD_CONNECTED=false
if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
    PHYSICAL_KEYBOARD_CONNECTED=true
    DISABLE_ROTATION=true
    echo "$(_ "Fyzická klávesnice: PŘIPOJENA")"
else
    echo "$(_ "Fyzická klávesnice: ODPOJENA")"
fi

# --- Automatický návrat z dočasných režimů ---
if [[ "$PHYSICAL_KEYBOARD_CONNECTED" == "true" && "$USER_STATE" == temporary-* ]]; then
    echo "$(_ "Klávesnice připojena → návrat do automatického režimu")"
    USER_STATE="automatic-enabled"
    echo "$USER_STATE" > "$STATE_FILE"
fi


# B) Výpočet finálního stavu spodního displeje
# Defaultně (Auto) platí: Klávesnice je připojená => Vypnout spodek.
ENABLE_BOTTOM_SCREEN=true
if [[ "$PHYSICAL_KEYBOARD_CONNECTED" == "true" ]]; then
    ENABLE_BOTTOM_SCREEN=false
fi

# C) Aplikace vynucených režimů (Overrides)
case "$USER_STATE" in
    enforce-primary-only)
        echo "$(_ "Vynuceno: Jen primární displej")"
        ENABLE_BOTTOM_SCREEN=false
        DISABLE_ROTATION=true
        ;;
    enforce-desktop)
        echo "$(_ "Vynuceno: Desktop mód (oba displeje)")"
        ENABLE_BOTTOM_SCREEN=true
        ;;
    automatic-enabled)
        echo "$(_ "Režim Auto: Klávesnice rozhoduje")"
        ;;
    temp-mirror)
        echo "$(_ "Dočasně: Zrcadlení displejů (auto rotace)")"
        ENABLE_BOTTOM_SCREEN=true
        FORCE_MIRROR=true
        ;;

    temp-reverse-mirror)
        echo "$(_ "Dočasně: Reverzní zrcadlení (180°)")"
        ENABLE_BOTTOM_SCREEN=true
        FORCE_MIRROR=true
        FORCE_REVERSE=true
        DISABLE_ROTATION=true
        ;;

    temp-primary-only)
        echo "$(_ "Dočasně: Pouze hlavní displej (bez rotace)")"
        ENABLE_BOTTOM_SCREEN=false
        DISABLE_ROTATION=true
        ;;
esac


# --- 4. Příprava proměnných pro rotaci (KDE/X11) ---
# Ponecháme logiku pro DISPLAY_ROTATION beze změny, jen ji sem zkopírujte
# nebo nechte, pokud editujete soubor. Zde pro úplnost:

DISPLAY_ROTATION="normal"
if [[ "$DISABLE_ROTATION" != "true" ]]; then
    case "$DIR" in
    *normal*)    DISPLAY_ROTATION="normal"   ;;
    *bottom-up*) DISPLAY_ROTATION="inverted" ;;
    *left-up*)   DISPLAY_ROTATION="left"     ;;
    *right-up*)  DISPLAY_ROTATION="right"    ;;
esac
fi

# --- 5. Aplikace nastavení (X11 / KDE / Wayland) ---

user=$USER
type=$XDG_SESSION_TYPE
desktop_env=$XDG_CURRENT_DESKTOP

if [[ "$user" == "sddm" ]]; then exit 0; fi

# === X11 ===
if [[ "$type" == "x11" ]]; then
    if [[ "$FORCE_MIRROR" == "true" ]]; then
        echo "$(_ "Aplikuji: Zrcadlení (X11)")"
        if [[ "$FORCE_REVERSE" == "true" ]]; then
            xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate inverted --output ${SECONDARY_DISPLAY_NAME} --rotate normal --auto --same-as ${PRIMARY_DISPLAY_NAME}
        else
            xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --output ${SECONDARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --auto --same-as ${PRIMARY_DISPLAY_NAME}
        fi
        exit 0
    fi
    # Zde používáme naši vypočtenou proměnnou ENABLE_BOTTOM_SCREEN
    if [[ "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        echo "$(_ "Aplikuji: Single Screen (X11)")"
        xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate normal --output ${SECONDARY_DISPLAY_NAME} --off
    else
        printf "$(_ "Aplikuji: Dual Screen (X11) - %s")\n" "$DISPLAY_ROTATION"
        case "$DISPLAY_ROTATION" in
            *left*) xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} ;;
            *right*) xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} ;;
            *inverted*) xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} ;;
            *normal*) xrandr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME} --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} ;;
        esac
    fi
    exit 0
fi

# === Wayland (KDE) ===
if [[ "$type" == "wayland" && "$desktop_env" == "KDE" ]]; then
    if [[ "$FORCE_MIRROR" == "true" ]]; then
        echo "$(_ "Aplikuji: Zrcadlení (KDE)")"

        if [[ "$FORCE_REVERSE" == "true" ]]; then
            kscreen-doctor output.$PRIMARY_DISPLAY_NAME.position.0,0 output.${PRIMARY_DISPLAY_NAME}.rotation.inverted \
                output.${SECONDARY_DISPLAY_NAME}.enable output.$SECONDARY_DISPLAY_NAME.position.0,0 output.${SECONDARY_DISPLAY_NAME}.rotation.normal
        else
            kscreen-doctor output.$PRIMARY_DISPLAY_NAME.position.0,0 output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION} \
                output.${SECONDARY_DISPLAY_NAME}.enable output.$SECONDARY_DISPLAY_NAME.position.0,0 output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}
        fi
        exit 0
    fi


    if [[ "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        printf "%s\n" "$(_ "Aplikuji: Single Screen (KDE)")"
        kscreen-doctor output.${PRIMARY_DISPLAY_NAME}.rotation.normal output.${SECONDARY_DISPLAY_NAME}.disable
    else
        printf "$(_ "Aplikuji: Dual Screen (KDE) - %s")\n" "$DISPLAY_ROTATION"
        kscreen-doctor output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION} output.${SECONDARY_DISPLAY_NAME}.enable output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}

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
                printf "$(_ "Neplatná orientace: %s")\n" "$DISPLAY_ROTATION"
                exit 1
                ;;
        esac

        echo "$PRIMARY_DISPLAY_NAME $PX,$PY,$PW,$PH"
        echo "$SECONDARY_DISPLAY_NAME $SX,$SY,$SW,$SH"

        # --- Výstup a nastavení ---
        printf "$(_ "Umísťuji %s (%s) od %s na souřadnice %s,%s")\n" "$SECONDARY_DISPLAY_NAME" "$DISPLAY_ROTATION" "$PRIMARY_DISPLAY_NAME" "$SX" "$SY"

        kscreen-doctor output.$PRIMARY_DISPLAY_NAME.position.$PX,$PY output.${PRIMARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION} \
            output.$SECONDARY_DISPLAY_NAME.position.$SX,$SY output.${SECONDARY_DISPLAY_NAME}.rotation.${DISPLAY_ROTATION}

    fi
    exit 0
fi

# === Wayland (Generic / wlroots) ===
if [[ "$type" == "wayland" ]]; then
    if [[ "$FORCE_MIRROR" == "true" ]]; then
        echo "$(_ "Aplikuji: Zrcadlení (Wlr)")"
        if [[ "$FORCE_REVERSE" == "true" ]]; then
            wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate inverted \
                --output ${SECONDARY_DISPLAY_NAME} --auto --rotate normal --same-as ${PRIMARY_DISPLAY_NAME}
        else
            wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} \
                --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} --same-as ${PRIMARY_DISPLAY_NAME}
        fi
        exit 0
    fi

    if [[ "$ENABLE_BOTTOM_SCREEN" == "false" ]]; then
        echo "$(_ "Aplikuji: Single Screen (Wlr)")"
        wlr-randr --output ${PRIMARY_DISPLAY_NAME} --rotate normal --output ${SECONDARY_DISPLAY_NAME} --off
    else
        printf "$(_ "Aplikuji: Dual Screen (Wlr) - %s")\n" "$DISPLAY_ROTATION"
        case "$DISPLAY_ROTATION" in
            *left*) wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} \
                --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --right-of ${SECONDARY_DISPLAY_NAME} ;;
            *right*) wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} \
                --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --left-of ${SECONDARY_DISPLAY_NAME} ;;
            *inverted*) wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} \
                --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --below ${SECONDARY_DISPLAY_NAME} ;;
            *normal*) wlr-randr --output ${SECONDARY_DISPLAY_NAME} --auto --rotate ${DISPLAY_ROTATION} \
                --output ${PRIMARY_DISPLAY_NAME} --rotate ${DISPLAY_ROTATION} --above ${SECONDARY_DISPLAY_NAME} ;;
        esac
    fi
    exit 0
fi
