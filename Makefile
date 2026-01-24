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

# Tato cesta slouží pro lokální build v adresáři projektu
BUILD_USR_DIR := $(USR_DIR)
USR_BIN := $(BUILD_USR_DIR)/bin
USR_SYSTEMD_SYSTEM := $(BUILD_USR_DIR)/lib/systemd/system
USR_SYSTEMD_USER := $(BUILD_USR_DIR)/lib/systemd/user

# DESTDIR je standardně prázdný (pro instalaci přímo do systému)
# PREFIX určuje cílovou cestu (obvykle /usr)
DESTDIR ?=
PREFIX ?= /usr

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
	@echo "Preparing user services"
	cp $(SRC_USER_SYSTEMD)/*.service $(USR_SYSTEMD_USER)/
else
	@echo "User services disabled"
	rm -f $(USR_SYSTEMD_USER)/*.service
endif

# -------------------------
# Install target (Klíčové pro Debian)
# -------------------------
.PHONY: install
install: all
	# Vytvoření cílových adresářů v DESTDIR
	install -d $(DESTDIR)$(PREFIX)/bin
	install -d $(DESTDIR)/lib/systemd/system
	install -d $(DESTDIR)$(PREFIX)/lib/systemd/user
	install -d $(DESTDIR)$(PREFIX)/share/asus-screen-toggle
	install -d $(DESTDIR)$(PREFIX)/lib/asus-screen-toggle/dispatcher

	# Instalace vygenerovaných a statických binárek/skriptů
	install -m 0755 $(USR_BIN)/asus-check-keyboard-system.sh $(DESTDIR)$(PREFIX)/bin/
	install -m 0755 $(BUILD_USR_DIR)/bin/asus-check-keyboard-genrules.sh $(DESTDIR)$(PREFIX)/bin/
	install -m 0755 $(BUILD_USR_DIR)/bin/asus-check-keyboard-user.sh $(DESTDIR)$(PREFIX)/bin/
	install -m 0755 $(BUILD_USR_DIR)/bin/asus-check-rotation.sh $(DESTDIR)$(PREFIX)/bin/
	install -m 0755 $(BUILD_USR_DIR)/bin/asus-screen-toggle-launcher.sh $(DESTDIR)$(PREFIX)/bin/
	install -m 0755 $(BUILD_USR_DIR)/bin/*.py $(DESTDIR)$(PREFIX)/bin/

	# Instalace systemd služeb
	install -m 0644 $(BUILD_USR_DIR)/lib/systemd/system/*.service $(DESTDIR)/lib/systemd/system/
	install -m 0644 $(USR_SYSTEMD_USER)/*.service $(DESTDIR)$(PREFIX)/lib/systemd/user/

	# Instalace asset a dalších souborů
	cp -r $(BUILD_USR_DIR)/share/* $(DESTDIR)$(PREFIX)/share/
	cp -r $(BUILD_USR_DIR)/lib/asus-screen-toggle/* $(DESTDIR)$(PREFIX)/lib/asus-screen-toggle/

# -------------------------
# Sanity checks
# -------------------------
.PHONY: check
check:
	@echo "Running sanity checks..."
	@test -d $(BUILD_USR_DIR) || (echo "ERROR: $(BUILD_USR_DIR)/ missing"; exit 1)
	@test -x $(USR_BIN)/asus-check-keyboard-system.sh || \
	    (echo "ERROR: dispatcher missing"; exit 1)
	@grep -q "DRM_CHANGE" $(USR_BIN)/asus-check-keyboard-system.sh || \
	    (echo "ERROR: DRM debounce missing"; exit 1)
ifeq ($(INSTALL_USER_SERVICE),yes)
	@test -f $(USR_SYSTEMD_USER)/asus-screen-toggle.service || \
	    (echo "ERROR: user service missing"; exit 1)
endif
	@echo "Sanity checks passed."

# -------------------------
# Clean
# -------------------------
.PHONY: clean
clean:
	rm -f $(USR_BIN)/asus-check-keyboard-system.sh
	rm -f $(USR_SYSTEMD_USER)/*.service
