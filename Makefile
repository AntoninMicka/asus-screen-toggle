# =========================
# asus-screen-toggle Makefile
# =========================

# -------------------------
# Paths
# -------------------------
SRC_DIR := src
# Adresář 'usr' v kořenu projektu slouží jako zdroj statických souborů
USR_DIR := usr
# Adresář pro dočasný build vygenerovaných souborů
BUILD_DIR := build_out

# Zdrojové cesty (v rámci src/)
SRC_BIN          := $(SRC_DIR)/bin
SRC_CHANNELS     := $(SRC_BIN)/channels
SRC_USER_SYSTEMD := $(SRC_DIR)/lib/systemd/user

# Build cesty (v rámci build_out/)
B_BIN  := $(BUILD_DIR)/bin
B_SYST := $(BUILD_DIR)/lib/systemd/system
B_USER := $(BUILD_DIR)/lib/systemd/user

# Instalace
DESTDIR ?=
PREFIX  ?= /usr

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
	mkdir -p $(B_BIN)
	mkdir -p $(B_SYST)
	mkdir -p $(B_USER)

# -------------------------
# System dispatcher (build-time)
# -------------------------
.PHONY: system-dispatcher
system-dispatcher:
	@echo "Building system dispatcher"
	cp $(CURDIR)/$(SRC_BIN)/asus-check-keyboard-system.sh.in $(B_BIN)/asus-check-keyboard-system.sh
	for ch in $(CHANNELS); do \
	  sed -i "/@CHANNEL_$$(echo $$ch | tr a-z A-Z)@/r $(CURDIR)/$(SRC_CHANNELS)/$$ch.sh" $(B_BIN)/asus-check-keyboard-system.sh; \
	  sed -i "/@CHANNEL_$$(echo $$ch | tr a-z A-Z)@/d" $(B_BIN)/asus-check-keyboard-system.sh; \
	done
	sed -i '/@CHANNEL_[A-Z_]\+@/d' $(B_BIN)/asus-check-keyboard-system.sh
	chmod 0755 $(B_BIN)/asus-check-keyboard-system.sh

# -------------------------
# User services (optional)
# -------------------------
.PHONY: user-services
user-services:
ifeq ($(INSTALL_USER_SERVICE),yes)
	@echo "Preparing user services"
	cp $(CURDIR)/$(SRC_USER_SYSTEMD)/*.service $(B_USER)/
else
	@echo "User services disabled"
endif

# -------------------------
# Install target (Klíčové pro Debian)
# -------------------------
.PHONY: install
install: all
	# Vytvoření adresářové struktury v DESTDIR
	install -d $(DESTDIR)$(PREFIX)/bin
	install -d $(DESTDIR)$(PREFIX)/lib/systemd/system
	install -d $(DESTDIR)$(PREFIX)/lib/systemd/user
	install -d $(DESTDIR)$(PREFIX)/share/asus-screen-toggle
	install -d $(DESTDIR)$(PREFIX)/lib/asus-screen-toggle/dispatcher
	install -d $(DESTDIR)$(PREFIX)/share/man/man1
	install -d $(DESTDIR)$(PREFIX)/share/man/cs/man1

	# 1. Instalace binárek BEZ PŘÍPON (řeší Lintian chyby a .desktop soubory)
	install -m 0755 $(B_BIN)/asus-check-keyboard-system.sh $(DESTDIR)$(PREFIX)/bin/asus-check-keyboard-system
	install -m 0755 $(USR_DIR)/bin/asus-check-keyboard-genrules.sh $(DESTDIR)$(PREFIX)/bin/asus-check-keyboard-genrules
	install -m 0755 $(USR_DIR)/bin/asus-check-keyboard-user.sh $(DESTDIR)$(PREFIX)/bin/asus-check-keyboard-user
	install -m 0755 $(USR_DIR)/bin/asus-check-rotation.sh $(DESTDIR)$(PREFIX)/bin/asus-check-rotation
	install -m 0755 $(USR_DIR)/bin/asus-screen-toggle-launcher.sh $(DESTDIR)$(PREFIX)/bin/asus-screen-toggle-launcher
	install -m 0755 $(USR_DIR)/bin/asus-screen-settings.py $(DESTDIR)$(PREFIX)/bin/asus-screen-settings
	install -m 0755 $(USR_DIR)/bin/asus-user-agent.py $(DESTDIR)$(PREFIX)/bin/asus-user-agent

	# 2. Systemd služby
	install -m 0644 $(USR_DIR)/lib/systemd/system/*.service $(DESTDIR)$(PREFIX)/lib/systemd/system/
	install -m 0644 $(B_USER)/*.service $(DESTDIR)$(PREFIX)/lib/systemd/user/

	# 3. Manuálové stránky (oprava cest pro Debian)
	install -m 0644 $(USR_DIR)/share/man/man1/*.1 $(DESTDIR)$(PREFIX)/share/man/man1/
	# Ošetření případu, kdy by adresář cs/ neexistoval
	if [ -d $(USR_DIR)/share/man/man1/cs ]; then \
	    install -m 0644 $(USR_DIR)/share/man/man1/cs/*.1 $(DESTDIR)$(PREFIX)/share/man/cs/man1/; \
	fi

	# 4. Ostatní data a template
	install -m 0644 $(USR_DIR)/share/99-asus-keyboard.rules.template $(DESTDIR)$(PREFIX)/share/asus-screen-toggle/
	cp -r $(USR_DIR)/share/applications $(DESTDIR)$(PREFIX)/share/
	cp -r $(USR_DIR)/share/asus-screen-toggle/*.svg $(DESTDIR)$(PREFIX)/share/asus-screen-toggle/
	cp -r $(USR_DIR)/lib/asus-screen-toggle/* $(DESTDIR)$(PREFIX)/lib/asus-screen-toggle/

# -------------------------
# Sanity checks
# -------------------------
.PHONY: check
check:
	@echo "Running sanity checks..."
	@test -x $(B_BIN)/asus-check-keyboard-system.sh || (echo "ERROR: build failed"; exit 1)
	@grep -q "DRM_CHANGE" $(B_BIN)/asus-check-keyboard-system.sh || (echo "ERROR: build corrupt"; exit 1)
	@echo "Sanity checks passed."

# -------------------------
# Clean
# -------------------------
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)

# -------------------------
# Dev git hooks
# -------------------------
.PHONY: dev-setup
dev-setup:
	@echo "Aktivuji Git hooky..."
	ln -sf ../../utilities/git-hooks/pre-push .git/hooks/pre-push
	ln -sf ../../utilities/git-hooks/post-checkout .git/hooks/post-checkout
	ln -sf ../../utilities/git-hooks/post-merge .git/hooks/post-merge
	chmod +x utilities/git-hooks/*
	@echo "Hooky jsou aktivní."
