#!/bin/bash

source /etc/asus-check-keyboard.cfg

export VENDOR_ID PRODUCT_ID PRIMARY_DISPLAY_NAME SECONDARY_DISPLAY_NAME LID

echo "vid $VENDOR_ID"
echo "pid $PRODUCT_ID"
echo "pd $PRIMARY_DISPLAY_NAME"
echo "sd $SECONDARY_DISPLAY_NAME"
echo "lid $LID"

envsubst < /usr/share/99-asus-keyboard.rules.template > /usr/lib/udev/rules.d/99-asus-keyboard.rules
