#!/bin/bash
# asus-check-keyboard-system.sh
# SYSTEM DISPATCHER – GENERATED AT BUILD TIME

set -euo pipefail

# -------------------------
# Constants / paths
# -------------------------
SELF="$(basename "$0")"
RUNTIME_DIR="/run/asus-screen-toggle"
LOG_TAG="asus-screen-toggle(system)"

# -------------------------
# DRM debounce
# -------------------------
debounce_drm() {
    local lock="/run/asus-screen-toggle/drm.lock"

    exec 9>"$lock" || return 1
    flock -n 9 || {
        log "DRM debounce: already handled, skipping"
        exit 0
    }

    log "DRM debounce: acquired lock, waiting for settle"
    sleep 0.5
}


# -------------------------
# Logging helpers
# -------------------------
log() {
    logger -t "$LOG_TAG" "$*"
}

die() {
    log "ERROR: $*"
    exit 1
}

# -------------------------
# Environment sanity
# -------------------------
mkdir -p "$RUNTIME_DIR" || die "Cannot create runtime dir"

# -------------------------
# Input (reason)
# -------------------------
REASON="${1:-UNKNOWN}"

case "$REASON" in
    USB_ADD|USB_REMOVE|DRM_CHANGE|UNKNOWN)
        ;;
    *)
        die "Invalid reason: $REASON"
        ;;
esac

log "Triggered with reason: $REASON"

# -------------------------
# Debounce for DRM only
# -------------------------

if [ "$REASON" = "DRM_CHANGE" ]; then
    debounce_drm
fi

# -------------------------
# Build-time injected body
# -------------------------
# The following section is injected during build.
# Do NOT edit manually.

@DISPATCH_BODY@

# -------------------------
# End
# -------------------------
exit 0
