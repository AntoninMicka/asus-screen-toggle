#!/bin/bash
# Skript pro vytvoření orig tarballu a sestavení podepsaného Debian balíčku

set -e

# 1. Získání verze z changelogu (pokud není zadána jako parametr)
VERSION_FULL=$(dpkg-parsechangelog -S Version)
VERSION_UPSTREAM=$(echo $VERSION_FULL | cut -d'-' -f1)
PACKAGE_NAME=$(dpkg-parsechangelog -S Source)

echo "--- Sestavování balíčku: $PACKAGE_NAME ($VERSION_FULL) ---"

# 2. Vytvoření .orig.tar.gz (vyžadováno pro non-native balíčky)
echo "Generuji upstream archiv (orig tarball)..."
tar --exclude='./debian' --exclude='./.git' --exclude='./.github' \
    -czf "../${PACKAGE_NAME}_${VERSION_UPSTREAM}.orig.tar.gz" .

# 3. Výběr GPG klíče pro podepisování
echo "Hledám dostupné GPG klíče..."
mapfile -t KEYS < <(gpg --list-secret-keys --with-colons | grep '^uid' | cut -d: -f10)

if [ ${#KEYS[@]} -eq 0 ]; then
    echo "CHYBA: Nenalezen žádný GPG klíč pro podepsání. Sestavuji nepodepsaný balíček."
    BUILD_OPTS="-us -uc"
else
    echo "Dostupné klíče:"
    for i in "${!KEYS[@]}"; do
        echo "  [$i] ${KEYS[$i]}"
    done

    read -p "Vyberte číslo klíče [0]: " KEY_INDEX
    KEY_INDEX=${KEY_INDEX:-0}
    SELECTED_KEY_UID=${KEYS[$KEY_INDEX]}

    # Získání ID klíče (long ID) pro debuild
    KEY_ID=$(gpg --list-keys --with-colons "$SELECTED_KEY_UID" | grep '^pub' | cut -d: -f5)
    echo "Vybrán klíč: $SELECTED_KEY_UID ($KEY_ID)"
    BUILD_OPTS="-k$KEY_ID"
fi

# 4. Sestavení balíčku pomocí debuild
# -sa vynutí zahrnutí původního zdroje (orig.tar.gz), což je nutné pro první upload na Mentors
echo "Spouštím debuild..."
debuild $BUILD_OPTS -sa

echo "--- Hotovo! Balíčky najdete v nadřazeném adresáři. ---"
