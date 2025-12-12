#!/bin/bash
# asus-user-agent.sh

# 1. Singleton check: Pokud už běžím, ukončím se.
# $$ je moje PID, grep -v $$ ho odfiltruje, abych nenašel sám sebe.
if pgrep -f "asus-user-agent.sh" | grep -v $$ > /dev/null; then
    echo "Agent už běží, končím."
    exit 0
fi

# 2. Funkce pro reakci na signál
obsluha_signalu() {
    echo "📩 Signál přijat! Spouštím rotaci..."
    # Voláme existující uživatelský skript, který už máte hotový
    /usr/bin/asus-check-keyboard-user.sh
}

# 3. Nastražení pastí
# SIGUSR1 = Spustí akci
# SIGTERM/SIGINT = Slušně ukončí skript (volitelné, ale dobré pro pořádek)
trap 'obsluha_signalu' SIGUSR1
trap 'exit 0' SIGTERM SIGINT

echo "Agent spuštěn (PID $$). Čekám na signál SIGUSR1..."

# 4. Nekonečná smyčka
# Použití 'wait' je trik, aby skript reagoval na signál okamžitě a nečekal na doběhnutí sleepu
while true; do
    sleep 1 & wait $!
done
