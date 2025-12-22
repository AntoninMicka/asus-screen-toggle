#!/bin/bash
set -e

SERVICE_NAME="asus-screen-toggle.service"
TEMPLATE_DIR="/usr/share/asus-screen-toggle"
TEMPLATE="$TEMPLATE_DIR/$SERVICE_NAME"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
USER_SERVICE="$USER_SYSTEMD_DIR/$SERVICE_NAME"

echo "▶️ Asus Screen Toggle – launcher"

# Musí běžet jako normální uživatel
if [[ $EUID -eq 0 ]]; then
    echo "❌ Tento launcher nesmí běžet jako root."
    exit 1
fi

# Kontrola šablony
if [[ ! -f "$TEMPLATE" ]]; then
    echo "❌ Chybí service šablona:"
    echo "   $TEMPLATE"
    exit 1
fi

# 1️⃣ Instalace service, pokud chybí nebo se liší
install_needed=false

if [[ ! -f "$USER_SERVICE" ]]; then
    install_needed=true
else
    if ! cmp -s "$TEMPLATE" "$USER_SERVICE"; then
        install_needed=true
    fi
fi

if $install_needed; then
    echo "🔧 Instaluji / aktualizuji user service"
    mkdir -p "$USER_SYSTEMD_DIR"
    install -m 0644 "$TEMPLATE" "$USER_SERVICE"
    systemctl --user daemon-reload
else
    echo "✅ User service je aktuální"
fi

# 2️⃣ Povolení služby (jen pokud není)
if ! systemctl --user is-enabled --quiet "$SERVICE_NAME"; then
    echo "🔔 Povoluji user service"
    systemctl --user enable "$SERVICE_NAME"
else
    echo "✅ User service je povolena"
fi

# 3️⃣ Zajištění běhu služby
if ! systemctl --user is-active --quiet "$SERVICE_NAME"; then
    echo "▶️ Spouštím user service"
    systemctl --user start "$SERVICE_NAME"
else
    echo "▶️ User service již běží"
fi

echo "🎉 Hotovo"
