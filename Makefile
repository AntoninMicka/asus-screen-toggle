# Makefile pro asus-screen-toggle

PREFIX ?= /usr
SYSCONFDIR ?= /etc
SYSTEMDUSERUNITDIR ?= $(PREFIX)/lib/systemd/user
SYSTEMDSYSTEMUNITDIR ?= $(PREFIX)/lib/systemd/system
UDEVRULESDIR ?= $(PREFIX)/lib/udev/rules.d

# Složky
SRC_DIR = asus-screen-toggle
PO_DIR = po
LOCALE_DIR = $(PREFIX)/share/locale

all: compile-locales

compile-locales:
	# Kompilace .po souborů do .mo
	for po in $(PO_DIR)/*.po; do \
		lang=$$(basename $$po .po); \
		mkdir -p build/locale/$$lang/LC_MESSAGES; \
		msgfmt $$po -o build/locale/$$lang/LC_MESSAGES/asus-screen-toggle.mo; \
	done

install:
	# 1. Instalace binárek (Python + Bash)
	install -d $(DESTDIR)$(PREFIX)/bin
	install -m 755 $(SRC_DIR)/usr/bin/*.py $(DESTDIR)$(PREFIX)/bin/
	install -m 755 $(SRC_DIR)/usr/bin/*.sh $(DESTDIR)$(PREFIX)/bin/

	# 2. Instalace sdílených dat (Ikony, Template)
	install -d $(DESTDIR)$(PREFIX)/share/asus-screen-toggle
	install -m 644 $(SRC_DIR)/usr/share/asus-screen-toggle/*.svg $(DESTDIR)$(PREFIX)/share/asus-screen-toggle/
	install -m 644 $(SRC_DIR)/usr/share/99-asus-keyboard.rules.template $(DESTDIR)$(PREFIX)/share/

	# 3. Instalace Desktop souborů
	install -d $(DESTDIR)$(PREFIX)/share/applications
	install -m 644 $(SRC_DIR)/usr/share/applications/*.desktop $(DESTDIR)$(PREFIX)/share/applications/

	# 4. Instalace Systemd služeb
	install -d $(DESTDIR)$(SYSTEMDUSERUNITDIR)
	install -m 644 $(SRC_DIR)/usr/lib/systemd/user/*.service $(DESTDIR)$(SYSTEMDUSERUNITDIR)/

	install -d $(DESTDIR)$(SYSTEMDSYSTEMUNITDIR)
	install -m 644 $(SRC_DIR)/usr/lib/systemd/system/*.service $(DESTDIR)$(SYSTEMDSYSTEMUNITDIR)/

	install -d $(DESTDIR)$(PREFIX)/lib/systemd/system-sleep
	install -m 755 $(SRC_DIR)/usr/lib/systemd/system-sleep/* $(DESTDIR)$(PREFIX)/lib/systemd/system-sleep/

	# 5. Instalace lokalizací (zkompilovaných)
	for lang in $$(ls build/locale); do \
		install -d $(DESTDIR)$(LOCALE_DIR)/$$lang/LC_MESSAGES; \
		install -m 644 build/locale/$$lang/LC_MESSAGES/asus-screen-toggle.mo \
			$(DESTDIR)$(LOCALE_DIR)/$$lang/LC_MESSAGES/; \
	done

clean:
	rm -rf build
