#!/bin/bash

# Přidat tuto sekci před sestavením balíčku:
echo "🌍 Zpracovávám lokalizace..."
if [ -f "./compile_locales.sh" ]; then
    ./compile_locales.sh
else
    echo "Varování: compile_locales.sh nenalezen!"
fi

dpkg-deb --root-owner-group --build asus-screen-toggle
