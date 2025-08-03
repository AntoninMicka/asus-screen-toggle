#!/bin/bash

# --- Nastavení ---
PRIMARY="eDP-1"
SECONDARY="DP-10"
ORIENTATION="$1"  # left, right, above, below

if [[ -z "$ORIENTATION" ]]; then
    echo "Použití: $0 [left|right|above|below]"
    #exit 1
fi

# --- Funkce pro získání geometrie z blokového výpisu ---
get_geometry_block() {
    local output="$1"
    #kscreen-doctor -o | awk -v out="eDP-1" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { print; exit }'
    #kscreen-doctor -o | awk -v out="eDP-1" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { print; split($2, pos, ","); split($3, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }'
    kscreen-doctor -o | awk -v out="$output" '$0 ~ "Output: " && $0 ~ out { in_block=1; next } in_block && $0 ~ "Geometry:" { split($3, pos, ","); split($4, res, "x"); print pos[1], pos[2], res[1], res[2]; exit }'
}

# --- Získání geometrie ---
read PX PY PW PH <<< "$(get_geometry_block "$PRIMARY")" || {
    echo "Chyba: nelze zjistit geometrii primárního výstupu $PRIMARY"
    exit 1
}

read SX SY SW SH <<< "$(get_geometry_block "$SECONDARY")"
if [[ -z "$SW" || -z "$SH" ]]; then
    echo "Upozornění: Sekundární výstup $SECONDARY není aktivní, použiji 1440x900"
    SW=1440
    SH=900
fi

echo "Primary   >$PX<, >$PY<, >$PW<, >$PH<"
echo "Secondary >$SX<, >$SY<, >$SW<, >$SH<"

# --- Výpočet nové pozice ---
case "$ORIENTATION" in
    left)
        NX=$((PX - SW))
        NY=$PY
        ;;
    right)
        NX=$((PX + PW))
        NY=$PY
        ;;
    above)
        NX=$PX
        NY=$((PY - SH))
        ;;
    below)
        NX=$PX
        NY=$((PY + PH))
        ;;
    *)
        echo "Neplatná orientace: $ORIENTATION"
        exit 1
        ;;
esac

# --- Výstup a aplikace ---
echo "Umísťuji $SECONDARY $ORIENTATION od $PRIMARY na pozici $NX,$NY"
#kscreen-doctor output.$SECONDARY.enable output.$SECONDARY.position.$NX,$NY
