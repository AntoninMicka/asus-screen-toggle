if [[ "${ENABLE_DIRECT_CALL:-false}" == "true" ]]; then

    if [[ "$type" == "x11" ]]; then
        display=$(loginctl show-session "$sid" -p Display --value)
        xauth_file="/home/$user/.Xauthority"
        [[ -f "$xauth_file" ]] || return 1

        sudo -u "$user" \
            env DISPLAY="$display" \
                XDG_SESSION_ID="$sid" \
                XDG_SESSION_TYPE="$type" \
                XDG_CURRENT_DESKTOP="$desktop" \
                XDG_RUNTIME_DIR="$runtime_path" \
                DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
            "$USER_BIN"
    fi

    if [[ "$type" == "wayland" ]]; then
        wayland_disp=$(loginctl show-session "$sid" -p WaylandDisplay --value)
        [[ -z "$wayland_disp" ]] && wayland_disp="wayland-0"

        sudo -u "$user" \
            env WAYLAND_DISPLAY="$wayland_disp" \
                XDG_SESSION_ID="$sid" \
                XDG_SESSION_TYPE="$type" \
                XDG_CURRENT_DESKTOP="$desktop" \
                XDG_RUNTIME_DIR="$runtime_path" \
                DBUS_SESSION_BUS_ADDRESS="$dbus_address" \
            "$USER_BIN"
    fi

    exit 0
fi
