#!/bin/bash
set -e

# Seznam služeb: worker (oneshot) a agent (systray)
SERVICES=("asus-screen-toggle.service" "asus-user-agent.service")

echo "▶️ Asus Screen Toggle – launcher"

# Kontrola, aby neběželo pod rootem (uživatelské služby spravuje uživatel)
if [[ $EUID -eq 0 ]]; then
    echo "❌ Tento launcher nesmí běžet jako root."
    exit 1
fi

# 1️⃣ Obnovení konfigurace systemd (načte změny v .service souborech)
systemctl --user daemon-reload

# 2️⃣ Aktivace a spuštění obou komponent
for SERVICE in "${SERVICES[@]}"; do
    echo "--- Správa jednotky: $SERVICE ---"

    # Povolení služby (aby se spouštěla automaticky při startu graphical-session)
    if ! systemctl --user is-enabled --quiet "$SERVICE"; then
        echo "🔔 Povoluji $SERVICE"
        systemctl --user enable "$SERVICE"
    else
        echo "✅ $SERVICE je povolena"
    fi

    # Spuštění služby
    # U oneshotu (worker) to provede nastavení, u simple (agent) to spustí tray ikonu
    echo "▶️ Spouštím/Restartuji $SERVICE"
    systemctl --user restart "$SERVICE"
done

echo "🎉 Hotovo – nastavení aplikováno a agent běží."
