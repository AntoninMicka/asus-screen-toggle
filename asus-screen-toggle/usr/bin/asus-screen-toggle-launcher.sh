#!/bin/bash
set -e

SERVICE_NAME="asus-screen-toggle.service"

echo "▶️ Asus Screen Toggle – launcher"

# Musí běžet jako normální uživatel
if [[ $EUID -eq 0 ]]; then
    echo "❌ Tento launcher nesmí běžet jako root."
    exit 1
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
