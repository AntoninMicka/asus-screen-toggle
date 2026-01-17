# Dispatch to user systemd service

log "Dispatching to user service for $TARGET"

runuser -u "#$TARGET_UID" -- \
    systemctl --user start asus-screen-toggle-user.service
