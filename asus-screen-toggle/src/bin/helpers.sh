prepare_user_context() {
    local sid="$1"

    user=$(loginctl show-session "$sid" -p Name --value)
    type=$(loginctl show-session "$sid" -p Type --value)
    desktop=$(loginctl show-session "$sid" -p Desktop --value)
    state=$(loginctl show-session "$sid" -p State --value)

    [[ "$state" == "active" ]] || return 1
    [[ "$user" != "sddm" && "$user" != "gdm" && "$user" != "lightdm" ]] || return 1
    [[ "$type" == "x11" || "$type" == "wayland" ]] || return 1

    USER_UID=$(loginctl show-session "$sid" -p User --value)

    runtime_path=$(loginctl show-session "$sid" -p RuntimePath --value)
    [[ -z "$runtime_path" ]] && runtime_path="/run/user/$USER_UID"

    dbus_address="unix:path=$runtime_path/bus"

    USER_BIN=$(command -v asus-check-keyboard-user || echo "/usr/bin/asus-check-keyboard-user")

    return 0
}
