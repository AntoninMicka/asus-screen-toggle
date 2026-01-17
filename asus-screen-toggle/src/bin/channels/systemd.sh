if [[ "${ENABLE_SYSTEMD_CALL:-false}" == "true" ]]; then
    if systemctl --user --machine="$USER_UID@.host" \
        start asus-screen-toggle.service \
        > /dev/null 2>&1; then
        exit 0
    fi
fi
