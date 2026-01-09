Asus Screen Toggle

Automatic secondary display management for Asus Zenbook Duo laptops on Linux (KDE/Debian).

Debian Mentors: https://mentors.debian.net/package/asus-screen-toggle/ ITP Bug: https://bugs.debian.org/1124010
Overview

This utility monitors your hardware state (lid status and external keyboard connection) to automatically enable or disable the secondary screen. It is specifically designed for the Asus Zenbook Duo (2024) UX8406.
Key Features

    Automatic Toggle: Enables/disables the bottom screen based on the keyboard connection.

    Smart Orientation: Full support for screen rotation via iio-sensor-proxy.

    User Interface: A GTK3 settings app and a system tray agent for manual overrides.

    Debian Integrated: Developed following Debian packaging standards.

Installation (Debian/KDE)

The package is currently in the process of being included in the official Debian repositories. You can download the latest version from Debian Mentors.
Build from source

    sudo apt install devscripts build-essential

    git clone https://github.com/antoninmicka/asus-screen-toggle

    cd asus-screen-toggle

    mk-build-deps -ir

    dpkg-buildpackage -us -uc

    sudo apt install ../asus-screen-toggle_*.deb

Documentation

Detailed documentation is available via manual pages:

    man asus-user-agent

    man asus-screen-settings

Or visit the Project Website: https://antoninmicka.github.io/asus-screen-toggle/
Compatibility

    Environment: Debian Sid/Testing/12 with KDE Plasma.

    Hardware: Asus Zenbook Duo (2024) UX8406.

    Dependencies: python3-gi, pydbus, gir1.2-appindicator3-0.1, iio-sensor-proxy.

License

This project is licensed under the GPL-3.0 License. Part of the Asus-Linux (https://asus-linux.org) community efforts.
