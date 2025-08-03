#!/bin/bash

# Identifikace klávesnice (uprav podle potřeby)
VENDOR_ID="0B05"
PRODUCT_ID="1BF2"

# Výstupní jméno displeje (změň podle `kscreen-doctor -o`)
DISPLAY_NAME="eDP-2"

# UID uživatele (uprav podle svého systému)
USER_UID=1000
XDG_SESSION_TYPE=wayland
WAYLAND_DISPLAY=wayland-0

# Nastavení prostředí
export XDG_RUNTIME_DIR="/run/user/$USER_UID"
export XDG_SESSION_TYPE=wayland
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0

if lsusb | grep -iq "${VENDOR_ID}:${PRODUCT_ID}"; then
    echo "Klávesnice detekována, vypínám spodní displej..."
    wlr-randr --output ${DISPLAY_NAME} --off
else
    echo "Klávesnice není připojena, zapínám spodní displej..."
    wlr-randr --output ${DISPLAY_NAME} --on
fi
