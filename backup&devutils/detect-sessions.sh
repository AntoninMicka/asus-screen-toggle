#!/bin/bash

echo "Uživatel | Session | Typ | Prostředí"

loginctl list-sessions --no-legend | while read sid user seat rest; do
    type=$(loginctl show-session "$sid" -p Type --value)
    display=$(loginctl show-session "$sid" -p Display --value)
    wayland=$(loginctl show-session "$sid" -p WaylandDisplay --value)

    env_type=0
    env_info="nelze zjistit"

    if [ "$type" = "tty" ]; then
        env_type=1
        env_info="textová konzole"
    elif [ "$type" = "x11" ]; then
        env_type=2
        env_info="DISPLAY=$display"
    elif [ "$type" = "wayland" ]; then
        env_type=3
        env_info="WAYLAND_DISPLAY=$wayland"
    fi

    echo "$user | $sid | $env_type | $env_info"
done

echo ""
echo "Uživatelé v grafickém prostředí (X11/Wayland):"
loginctl list-sessions --no-legend | while read sid user seat rest; do
    type=$(loginctl show-session "$sid" -p Type --value)
    if [[ "$type" == "x11" || "$type" == "wayland" ]]; then
        display=$(loginctl show-session "$sid" -p Display --value)
        wayland=$(loginctl show-session "$sid" -p WaylandDisplay --value)
        echo "$user | $sid | $type | DISPLAY=$display WAYLAND_DISPLAY=$wayland"
    fi
done
