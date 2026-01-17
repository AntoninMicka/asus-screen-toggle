# Dispatch to user systemd service

log "Dispatching to user service"

systemctl --user start asus-screen-toggle-user.service
