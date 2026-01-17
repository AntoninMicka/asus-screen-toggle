#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# 0. Ne v CI
# ------------------------------------------------------------
if [[ -n "${CI:-}" ]]; then
  echo "ERROR: Refusing to run in CI"
  exit 1
fi

# ------------------------------------------------------------
# 1. Jsme na main?
# ------------------------------------------------------------
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
TAG="v$UPSTREAM_VERSION"

echo "Debian version   : $DEB_VERSION"
echo "Upstream version : $UPSTREAM_VERSION"
echo "Tag              : $TAG"

# ------------------------------------------------------------
# 4. Tag nesmí existovat
# ------------------------------------------------------------
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: Tag $TAG already exists"
  exit 1
fi

# ------------------------------------------------------------
# 5. Potvrzení
# ------------------------------------------------------------
echo
read -rp "Proceed with release? [y/N] " ans
[[ "$ans" == "y" ]] || exit 1

# ------------------------------------------------------------
# 6. Vytvoř annotated tag
# ------------------------------------------------------------
git tag -a "$TAG" -m "Release $UPSTREAM_VERSION"
git push origin "$TAG"

# ------------------------------------------------------------
# 7. Build Debian source
# ------------------------------------------------------------
echo "Building Debian source package"
rm -rf .pc || true
dpkg-buildpackage -S -sa

# ------------------------------------------------------------
# 8. Upload na mentors
# ------------------------------------------------------------
CHANGES=$(ls ../*_source.changes)

echo "Uploading $CHANGES to mentors"
dput mentors "$CHANGES"

echo
echo "Release $UPSTREAM_VERSION successfully uploaded"
