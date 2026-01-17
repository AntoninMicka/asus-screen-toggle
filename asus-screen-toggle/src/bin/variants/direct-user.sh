# Direct call to user worker

log "Calling user worker directly"

# předpokládá správné prostředí (XDG_RUNTIME_DIR, DISPLAY, WAYLAND_DISPLAY)
su "$TARGET_USER" -c "/usr/bin/asus-check-keyboard-user.sh '$REASON'"
