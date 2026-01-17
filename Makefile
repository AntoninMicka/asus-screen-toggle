# =========================
# asus-screen-toggle Makefile
# =========================

# -------------------------
# Paths
# -------------------------
SRC_DIR := src
USR_DIR := usr

SRC_BIN := $(SRC_DIR)/bin
SRC_CHANNELS := $(SRC_BIN)/channels
SRC_USER_SYSTEMD := $(SRC_DIR)/lib/systemd/user

USR_BIN := $(USR_DIR)/bin
USR_SYSTEMD_SYSTEM := $(USR_DIR)/lib/systemd/system
USR_SYSTEMD_USER := $(USR_DIR)/lib/systemd/user

# -------------------------
# Build config
# -------------------------
-include build.conf

CHANNELS ?= systemd dbus signal direct
INSTALL_USER_SERVICE ?= yes

# -------------------------
# Default target
# -------------------------
.PHONY: all
all: prepare system-dispatcher user-services

# -------------------------
# Prepare directories
# -------------------------
.PHONY: prepare
prepare:
	mkdir -p $(USR_BIN)
	mkdir -p $(USR_SYSTEMD_SYSTEM)
	mkdir -p $(USR_SYSTEMD_USER)

# -------------------------
# System dispatcher (build-time)
# -------------------------
.PHONY: system-dispatcher
system-dispatcher:
	@echo "Building system dispatcher"
	cp $(SRC_BIN)/asus-check-keyboard-system.sh.in \
	   $(USR_BIN)/asus-check-keyboard-system.sh
	for ch in $(CHANNELS); do \
	  sed -i "/@CHANNEL_$$(echo $$ch | tr a-z A-Z)@/r $(SRC_CHANNELS)/$$ch.sh" \
	      $(USR_BIN)/asus-check-keyboard-system.sh; \
	  sed -i "/@CHANNEL_$$(echo $$ch | tr a-z A-Z)@/d" \
	      $(USR_BIN)/asus-check-keyboard-system.sh; \
	done
	sed -i '/@CHANNEL_[A-Z_]\+@/d' \
	    $(USR_BIN)/asus-check-keyboard-system.sh
	chmod 0755 $(USR_BIN)/asus-check-keyboard-system.sh

# -------------------------
# User services (optional)
# -------------------------
.PHONY: user-services
user-services:
ifeq ($(INSTALL_USER_SERVICE),yes)
	@echo "Installing user services"
	cp $(SRC_USER_SYSTEMD)/*.service $(USR_SYSTEMD_USER)/
else
	@echo "User services disabled"
	rm -f $(USR_SYSTEMD_USER)/*.service
endif

# -------------------------
# Sanity checks
# -------------------------
.PHONY: check
check:
	@echo "Running sanity checks..."

	@test -d usr || (echo "ERROR: usr/ missing"; exit 1)
	@test -x usr/bin/asus-check-keyboard-system.sh || \
		(echo "ERROR: dispatcher missing"; exit 1)

	@grep -q "DRM_CHANGE" usr/bin/asus-check-keyboard-system.sh || \
		(echo "ERROR: DRM debounce missing"; exit 1)

ifeq ($(INSTALL_USER_SERVICE),yes)
	@test -f usr/lib/systemd/user/asus-screen-toggle.service || \
		(echo "ERROR: user service missing"; exit 1)
endif

	@find usr -type f \( -name '*.in' -o -name 'build.conf' \) | \
		grep -q . && \
		(echo "ERROR: build-time files leaked"; exit 1) || true

	@echo "Sanity checks passed."

# -------------------------
# Clean
# -------------------------
.PHONY: clean
clean:
	rm -f $(USR_BIN)/asus-check-keyboard-system.sh
	rm -f $(USR_SYSTEMD_USER)/*.service
