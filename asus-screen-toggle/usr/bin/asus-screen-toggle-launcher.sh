#!/bin/bash
set -e

SERVICE_NAME="asus-screen-toggle.service"

echo "▶️ Asus Screen Toggle – launcher"

# Musí běžet jako normální uživatel
if [[ $EUID -eq 0 ]]; then
    echo "❌ Tento launcher nesmí běžet jako root."
    exit 1
fi

USER_NAME="${SUDO_USER:-$USER}"

if ! loginctl show-user "$USER_NAME" -p Linger --value 2>/dev/null | grep -qx yes; then
    echo "Enabling linger for user: $USER_NAME"

    if [ "$(id -u)" -ne 0 ]; then
        echo "ERROR: loginctl enable-linger requires root privileges"
        exit 1
    fi

    loginctl enable-linger "$USER_NAME"
fi

systemctl --user daemon-reload

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
