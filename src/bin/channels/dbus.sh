if [[ "${ENABLE_DBUS:-false}" == "true" ]]; then
    if sudo -u "$user" DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
        dbus-send --session --print-reply --reply-timeout=1000 \
        --dest=org.asus.ScreenToggle \
        /org/asus/ScreenToggle org.asus.ScreenToggle.Trigger \
        > /dev/null 2>&1; then
        exit 0
    fi
fi
