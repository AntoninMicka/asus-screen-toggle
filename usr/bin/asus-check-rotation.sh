#!/bin/bash

ROTATION=""

CHECH_BIN=$(command -v asus-check-keyboard-system || echo "/usr/bin/asus-check-keyboard-system")

monitor-sensor | while read -r line; do
  case "$line" in
    *"normal"*)      NEW_ROT="normal" ;;
    *"bottom-up"*)   NEW_ROT="inverted" ;;
    *"left-up"*)     NEW_ROT="left" ;;
    *"right-up"*)    NEW_ROT="right" ;;
    *) continue ;;  # jiné informace ignorujeme
  esac

  if [[ "$NEW_ROT" != "$ROTATION" ]]; then
    ROTATION="$NEW_ROT"
    echo "Nová orientace: $ROTATION"
    echo "DIR=\"$line\"" > /tmp/asus-rotation
    $CHECH_BIN
  fi

  sleep 3
done
