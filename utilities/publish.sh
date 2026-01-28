#!/usr/bin/env bash
set -euo pipefail

#!/bin/bash
set -e

echo "--- Zahajuji proces nahrávání na Debian Mentors ---"

# 1. Vyčištění předchozích buildů (aby se nahrála správná verze)
rm -f ../asus-screen-toggle_*.changes
rm -f ../asus-screen-toggle_*.dsc
rm -f ../asus-screen-toggle_*.upload

# 2. Sestavení SOURCE balíčku
# -S  = source only (vhodné pro Architecture: all na Mentors)
# -sa = vynutit orig.tar.gz
echo "Sestavuji zdrojový balíček (source-only)..."
./utilities/debian_build.sh -S -sa

# 3. Automatické vyhledání .changes souboru
# Hledáme jakýkoliv .changes soubor v nadřazeném adresáři
CHANGES_FILE=$(ls -t ../asus-screen-toggle_*.changes 2>/dev/null | head -n 1)

if [ -z "$CHANGES_FILE" ]; then
    echo "CHYBA: Nebyl nalezen žádný soubor .changes v adresáři .."
    exit 1
fi

echo "Nalezen soubor pro nahrání: $CHANGES_FILE"

# 4. Kontrola integrity (dsc musí být uvnitř)
if ! grep -q "\.dsc" "$CHANGES_FILE"; then
    echo "VAROVÁNÍ: Soubor .changes neobsahuje .dsc. Mentors ho odmítnou."
    echo "Zkuste spustit: debuild -S -sa"
    exit 1
fi

# 5. Samotné nahrání
echo "Spouštím dput..."
dput mentors "$CHANGES_FILE"

echo "--- Hotovo. Sledujte e-mail od mentors.debian.net ---"
