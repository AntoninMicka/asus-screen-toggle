# =========================
# Project build Makefile
# =========================

# directories
SRC_DIR := src
USR_DIR := usr

SRC_BIN := $(SRC_DIR)/bin
SRC_USER_SYSTEMD := $(SRC_DIR)/lib/systemd/user

USR_BIN := $(USR_DIR)/bin
USR_SYSTEMD_SYSTEM := $(USR_DIR)/lib/systemd/system
USR_SYSTEMD_USER := $(USR_DIR)/lib/systemd/user

# build config
-include build.conf

INSTALL_USER_SERVICE ?= yes

# files
SYSTEM_DISPATCHER_SRC := $(SRC_BIN)/asus-check-keyboard-system.sh
SYSTEM_DISPATCHER_DST := $(USR_BIN)/asus-check-keyboard-system.sh

USER_SERVICES_SRC := $(wildcard $(SRC_USER_SYSTEMD)/*.service)
USER_SERVICES_DST := $(patsubst $(SRC_USER_SYSTEMD)/%, \
                      $(USR_SYSTEMD_USER)/%, \
                      $(USER_SERVICES_SRC))

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
# System dispatcher
# -------------------------
.PHONY: system-dispatcher
system-dispatcher: $(SYSTEM_DISPATCHER_DST)

$(SYSTEM_DISPATCHER_DST): $(SYSTEM_DISPATCHER_SRC)
	@echo "Building system dispatcher"
	cp $< $@
	chmod 0755 $@

# -------------------------
# User services (optional)
# -------------------------
.PHONY: user-services
user-services:
ifeq ($(INSTALL_USER_SERVICE),yes)
	@echo "Installing user services"
	cp $(USER_SERVICES_SRC) $(USR_SYSTEMD_USER)/
else
	@echo "User services disabled by build config"
	rm -f $(USR_SYSTEMD_USER)/*.service
endif

# -------------------------
# Clean generated files
# -------------------------
.PHONY: clean
clean:
	rm -rf $(USR_BIN)/asus-check-keyboard-system.sh
	rm -f $(USR_SYSTEMD_USER)/*.service

# -------------------------
# Sanity checks
# -------------------------
.PHONY: check
check:
	@echo "Running sanity checks..."

	@test -d usr || (echo "ERROR: usr/ directory missing"; exit 1)

	@test -x usr/bin/asus-check-keyboard-system.sh || \
		(echo "ERROR: system dispatcher missing or not executable"; exit 1)

	@grep -q "@DISPATCH_BODY@" usr/bin/asus-check-keyboard-system.sh && \
		(echo "ERROR: dispatcher still contains build placeholder"; exit 1) || true

ifeq ($(INSTALL_USER_SERVICE),yes)
	@test -f usr/lib/systemd/user/asus-screen-toggle.service || \
		(echo "ERROR: user service expected but missing"; exit 1)
else
	@test ! -e usr/lib/systemd/user/asus-screen-toggle.service || \
		(echo "ERROR: user service present but should not be installed"; exit 1)
endif

	@find usr -type f \( -name '*.in.sh' -o -name 'build.conf' \) | \
		grep -q . && \
		(echo "ERROR: build-time sources leaked into usr/"; exit 1) || true

	@grep -q "debounce_drm" usr/bin/asus-check-keyboard-system.sh || \
		(echo "ERROR: DRM debounce missing"; exit 1)

	@grep -q "get_active_user" usr/bin/asus-check-keyboard-system.sh || \
		(echo "ERROR: user selection logic missing"; exit 1)

	@echo "Sanity checks passed."
