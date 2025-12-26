#!/bin/bash
# Skript pro generování a aktualizaci překladů (gettext)

DOMAIN="asus-screen-toggle"
LOCALE_DIR="po"
FILES_PY="asus-screen-toggle/usr/bin/*.py"
FILES_SH="asus-screen-toggle/usr/bin/*.sh"

mkdir -p "$LOCALE_DIR"

echo "1. Extrahování řetězců z Pythonu a Shellu..."
# Vytvoření šablony (.pot)
# -k_: Klíčové slovo pro python je _
# --from-code=UTF-8: Kódování
xgettext -L Python -k_ -o "$LOCALE_DIR/$DOMAIN.pot" $FILES_PY --from-code=UTF-8
# Připojíme řetězce ze Shell skriptů (-j = join)
xgettext -L Shell -k_ -j -o "$LOCALE_DIR/$DOMAIN.pot" $FILES_SH --from-code=UTF-8

echo "Šablona vytvořena: $LOCALE_DIR/$DOMAIN.pot"

# Seznam jazyků
LANGS=("en" "cs" "fr" "es" "pt" "zh" "ja" "ar")

for lang in "${LANGS[@]}"; do
    PO_FILE="$LOCALE_DIR/$lang.po"

    if [ -f "$PO_FILE" ]; then
        echo "Aktualizuji $lang.po ..."
        msgmerge -U "$PO_FILE" "$LOCALE_DIR/$DOMAIN.pot"
    else
        echo "Vytvářím nový $lang.po ..."
        msginit --no-translator -l "$lang" -o "$PO_FILE" -i "$LOCALE_DIR/$DOMAIN.pot"
    fi
done

echo "Hotovo. Nyní upravte soubory .po v adresáři $LOCALE_DIR/ a doplňte překlady."
echo "Pro kompilaci (test) spusťte: bash compile_locales.sh"
