#!/bin/bash
# Kompilace .po do .mo

DOMAIN="asus-screen-toggle"
SRC_DIR="po"
# Cílová složka v balíčku
DEST_DIR="asus-screen-toggle/usr/share/locale"

echo "Kompiluji překlady..."

for po_file in "$SRC_DIR"/*.po; do
    lang=$(basename "$po_file" .po)
    # Odstranění .UTF-8 suffixu pokud tam je, systémové složky jsou obvykle jen 'cs', 'en'
    lang=${lang%%.*}

    target_dir="$DEST_DIR/$lang/LC_MESSAGES"
    mkdir -p "$target_dir"

    echo "  $lang -> $target_dir/$DOMAIN.mo"
    msgfmt "$po_file" -o "$target_dir/$DOMAIN.mo"
done
