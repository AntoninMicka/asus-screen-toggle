#!/bin/bash

echo "🏗️  Příprava lokalizací..."
# Ujistíme se, že složka existuje
chmod +x ./compile_locales.sh
./compile_locales.sh

dpkg-deb --root-owner-group --build asus-screen-toggle
