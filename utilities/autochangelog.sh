#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
DIST="unstable"
URGENCY="medium"

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
COMMITS_RANGE="${LAST_TAG}..HEAD"

# ------------------------------------------------------------
# Získat commity
# ------------------------------------------------------------
COMMITS=$(git log --no-merges --pretty=format:%s $COMMITS_RANGE)

[[ -n "$COMMITS" ]] || {
  echo "No commits since last tag"
  exit 1
}

# ------------------------------------------------------------
# Rozhodnout bump
# ------------------------------------------------------------
BUMP="patch"

echo "$COMMITS" | grep -q '^BREAKING:' && BUMP="major"
echo "$COMMITS" | grep -q '^feat:' && [[ "$BUMP" != "major" ]] && BUMP="minor"

# ------------------------------------------------------------
# Aktuální verze
# ------------------------------------------------------------
if [[ -n "$LAST_TAG" ]]; then
  BASE_VERSION="${LAST_TAG#v}"
else
  BASE_VERSION="0.0.0"
fi

IFS=. read -r MAJOR MINOR PATCH <<<"$BASE_VERSION"

case "$BUMP" in
  major) MAJOR=$((MAJOR+1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR+1)); PATCH=0 ;;
  patch) PATCH=$((PATCH+1)) ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo "Bump type : $BUMP"
echo "New ver.  : $NEW_VERSION"

# ------------------------------------------------------------
# Vygenerovat changelog
# ------------------------------------------------------------
dch --newversion "$NEW_VERSION-1" \
    --distribution "$DIST" \
    --urgency "$URGENCY" \
    "Automated release"

# ------------------------------------------------------------
# Přidat commity do changelogu
# ------------------------------------------------------------
while read -r line; do
  case "$line" in
    fix:*|feat:*|BREAKING:*)
      dch -a "  * ${line#*: }"
      ;;
  esac
done <<<"$COMMITS"

echo "Changelog updated. Review before committing."
