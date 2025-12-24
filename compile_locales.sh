#!/bin/bash
# gen_locales.sh
# Skript pro extrakci textů a aktualizaci .po souborů

DOMAIN="asus-screen-toggle"
PO_DIR="po"
SRC_DIR="asus-screen-toggle/usr/bin"

# Seznam podporovaných jazyků
LANGS=("en" "cs" "fr" "es" "pt" "zh" "ja" "ar")

mkdir -p "$PO_DIR"

echo "1. Extrahování řetězců..."

# Vytvoření šablony (.pot)
# Python soubory
xgettext -L Python -k_ --from-code=UTF-8 -o "$PO_DIR/$DOMAIN.pot" "$SRC_DIR"/*.py

# Bash soubory (připojíme k existující šabloně pomocí -j)
xgettext -L Shell -k_ --from-code=UTF-8 -j -o "$PO_DIR/$DOMAIN.pot" "$SRC_DIR"/*.sh

echo "Šablona vytvořena: $PO_DIR/$DOMAIN.pot"

# Aktualizace/Vytvoření .po souborů pro jednotlivé jazyky
for lang in "${LANGS[@]}"; do
    PO_FILE="$PO_DIR/$lang.po"

    if [ -f "$PO_FILE" ]; then
        echo "🔄 Aktualizuji $lang.po ..."
        msgmerge -U --backup=none "$PO_FILE" "$PO_DIR/$DOMAIN.pot"
    else
        echo "✨ Vytvářím nový $lang.po ..."
        msginit --no-translator -l "$lang" -o "$PO_FILE" -i "$PO_DIR/$DOMAIN.pot"

        # Oprava charsetu, msginit někdy nastaví ASCII
        sed -i 's/Content-Type: text\/plain; charset=ASCII/Content-Type: text\/plain; charset=UTF-8/' "$PO_FILE"
    fi
done

echo "✅ Hotovo. Nyní přeložte soubory v adresáři $PO_DIR/"
