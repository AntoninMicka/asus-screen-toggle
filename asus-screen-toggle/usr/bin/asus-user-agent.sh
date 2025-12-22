#!/bin/bash

### 1. Singleton Check (Robustní verze s flock)
# Otevřeme soubor zámku na deskriptoru 200
LOCKFILE="/tmp/asus-user-agent.lock"
exec 200> "$LOCKFILE"

# Pokusíme se získat exkluzivní zámek (-x) bez čekání (-n).
# Pokud to nejde (jiná instance už ho má), skončíme.
if ! flock -n -x 200; then
    echo "Agent už běží (zámek je aktivní)."
    exit 1
fi

### 2. Konfigurace a Cesty
APP_NAME="asus-check-keyboard"
STATE_DIR="$HOME/.local/state/$APP_NAME"
STATE_FILE="$STATE_DIR/state"
LOGIC_SCRIPT="/usr/bin/asus-check-keyboard-user.sh"
ICON_PATH="/usr/share/asus-screen-toggle"

# Ikony (ujistěte se, že existují, jinak yad nezobrazí nic)
ICON_AUTO="$ICON_PATH/icon-green.png"
ICON_PRIMARY="$ICON_PATH/icon-red.png"
ICON_DESKTOP="$ICON_PATH/icon-blue.png"
# Fallback ikony ze systému, kdyby vaše neexistovaly
[ -f "$ICON_AUTO" ] || ICON_AUTO="input-tablet"
[ -f "$ICON_PRIMARY" ] || ICON_PRIMARY="video-display"
[ -f "$ICON_DESKTOP" ] || ICON_DESKTOP="computer"

# Načtení configu (pokud existuje)
[ -f /etc/asus-check-keyboard.cfg ] && source /etc/asus-check-keyboard.cfg

### 3. Příprava roury (Pipe) pro YAD
PIPE=$(mktemp -u /tmp/asus_tray_XXXX.fifo)
mkfifo "$PIPE"
# Trik: Otevřeme rouru na deskriptoru 3 pro čtení i zápis.
# To zajistí, že roura zůstane "živá", i když do ní nikdo zrovna nepíše.
exec 3<> "$PIPE"

# Úklid při ukončení
cleanup() {
    rm -f "$PIPE"
    kill $YAD_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

### 4. Funkce pro nastavení stavu a ikony
update_tray() {
    # 1. Přečíst stav (buď z argumentu, nebo ze souboru)
    if [ -n "$1" ]; then
        CURRENT_STATE="$1"
        # Uložit nový stav
        mkdir -p "$STATE_DIR"
        echo "$CURRENT_STATE" > "$STATE_FILE"
    elif [ -f "$STATE_FILE" ]; then
        CURRENT_STATE=$(<"$STATE_FILE")
    else
        CURRENT_STATE="automatic-enabled"
    fi

    echo "Stav: $CURRENT_STATE"

    # 2. Poslat příkazy do YADu přes rouru (fd 3)
    case "$CURRENT_STATE" in
        automatic-enabled)
            echo "icon:$ICON_AUTO" >&3
            echo "tooltip:Automaticky režim" >&3
            ;;
        enforce-primary-only)
            echo "icon:$ICON_PRIMARY" >&3
            echo "tooltip:Vynuceno: Jen primární" >&3
            ;;
        enforce-desktop)
            echo "icon:$ICON_DESKTOP" >&3
            echo "tooltip:Vynuceno: Desktop mód" >&3
            ;;
    esac
}

# Funkce, která provede logiku přepnutí obrazovek
apply_logic() {
    echo "Spouštím logiku obrazovek..."
    bash "$LOGIC_SCRIPT" &
}

### 5. Zpracování kliknutí z menu (Běží na pozadí)
handle_click() {
    local action="$1"
    echo "Kliknuto: $action"
    case "$action" in
        set_auto)
            update_tray "automatic-enabled"
            apply_logic
            ;;
        set_primary)
            update_tray "enforce-primary-only"
            apply_logic
            ;;
        set_desktop)
            update_tray "enforce-desktop"
            apply_logic
            ;;
        trigger_check)
            # Jen spustíme kontrolu (např. signál od Udevu)
            apply_logic
            # Po kontrole se může změnit stav (např. detekce rotace),
            # ale to by měl řešit logic script zápisem do state file?
            # Pro jistotu jen překreslíme ikonu dle aktuálního souboru
            update_tray
            ;;
        quit)
            cleanup
            exit 0
            ;;
    esac
}

### 6. Spuštění YAD (Tray Icon)
# GDK_BACKEND=x11: Nutné pro Wayland, jinak se nezobrazí ikona
# <&3 : Čte příkazy z naší roury
# > >(...) : Výstup (kliknutí) posíláme rovnou do smyčky, která volá handle_click
env GDK_BACKEND=x11 yad --notification --listen \
    --image="$ICON_AUTO" \
    --text="ASUS Control" \
    --menu="Automaticky ! echo set_auto | \
            Jen primární ! echo set_primary | \
            Desktop mód ! echo set_desktop | \
            Zkontrolovat ! echo trigger_check | \
            Ukončit ! echo quit" \
    <&3 > >(while read -r line; do handle_click "$line"; done) &

YAD_PID=$!

### 7. Hlavní smyčka a Signály
# Když Udev pošle SIGUSR1, překreslíme tray a spustíme logiku
trap 'update_tray; apply_logic' SIGUSR1

echo "Agent spuštěn (PID $$). YAD PID: $YAD_PID"

# Inicializace stavu po startu
update_tray

# HLAVNÍ SMYČKA
# 'wait' se ukončí při každém signálu (SIGUSR1).
# Proto ho voláme ve smyčce, dokud proces YAD skutečně běží.
while kill -0 $YAD_PID 2>/dev/null; do
    wait $YAD_PID
done

# Úklid, pokud YAD spadne sám od sebe
rm -f "$PIPE
