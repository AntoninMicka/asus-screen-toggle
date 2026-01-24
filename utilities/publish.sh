#!/bin/bash
set -e

echo "--- Zahajuji proces nahrávání na servery ---"

# 1. Čištění a příprava
make clean
rm -f ../asus-screen-toggle_*.orig.tar.gz

# 2. Build balíčku (použije váš dříve vytvořený build proces)
# Předpokládáme, že build skript vygeneruje podepsaný .changes soubor
./utilities/debian_build.sh

# 3. Identifikace .changes souboru
CHANGES_FILE=$(ls -t ../asus-screen-toggle_*_source.changes | head -n 1)

# 4. Nahrání na Debian Mentors (vyžaduje dput balíček a nastavení v ~/.dput.cf)
echo "Nahrávám $CHANGES_FILE na mentors.debian.net..."
dput mentors "$CHANGES_FILE"

# 5. Volitelně: Nahrání na váš vlastní server přes SCP/RSYNC
# rsync -avP ../*.deb user@vasserver:/var/www/repo/binary/

echo "--- Publish dokončen ---"
