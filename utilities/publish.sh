#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# 0. Ochrany
# ------------------------------------------------------------
[[ -n "${CI:-}" ]] && {
  echo "ERROR: Refusing to run in CI"
  exit 1
}

# ------------------------------------------------------------
# 1. Jsme v git repu a na main
# ------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null

BRANCH=$(git symbolic-ref --short HEAD)
if [[ "$BRANCH" != "main" ]]; then
  echo "ERROR: Not on main branch (current: $BRANCH)"
  exit 1
fi

# ------------------------------------------------------------
# 2. Čistý strom
# ------------------------------------------------------------
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: Working tree is dirty"
  exit 1
fi

# ------------------------------------------------------------
# 3. Verze z changelogu
# ------------------------------------------------------------
DEB_VERSION=$(dpkg-parsechangelog -S Version)
UPSTREAM_VERSION=${DEB_VERSION%-*}
PKG_NAME=$(dpkg-parsechangelog -S Source)

TAR="../${PKG_NAME}_${UPSTREAM_VERSION}.orig.tar.gz"

echo "Package  : $PKG_NAME"
echo "Version  : $DEB_VERSION"
echo "Upstream : $UPSTREAM_VERSION"
echo "Tarball  : $TAR"

# ------------------------------------------------------------
# 4. Potvrzení
# ------------------------------------------------------------
echo
read -rp "Build & upload this version? [y/N] " ans
[[ "$ans" == "y" ]] || exit 1

# ------------------------------------------------------------
# 5. Vytvoř upstream tarball
# ------------------------------------------------------------
if [[ -f "$TAR" ]]; then
  echo "Upstream tarball already exists: $TAR"
else
  echo "Creating upstream tarball"
  git archive \
    --format=tar.gz \
    --prefix=${PKG_NAME}-${UPSTREAM_VERSION}/ \
    HEAD \
    > "$TAR"
fi

# ------------------------------------------------------------
# 6. Build Debian source balíčku
# ------------------------------------------------------------
echo "Building Debian source package"
rm -rf .pc || true
dpkg-buildpackage -S -sa

# ------------------------------------------------------------
# 7. Upload na mentors
# ------------------------------------------------------------
CHANGES="../${PKG_NAME}_${DEB_VERSION}_source.changes"

if [[ ! -f "$CHANGES" ]]; then
  echo "ERROR: Changes file not found: $CHANGES"
  exit 1
fi

echo "Uploading $CHANGES to mentors"
dput mentors "$CHANGES"

echo
echo "Upload finished successfully"
