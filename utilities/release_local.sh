#!/usr/bin/env bash
set -euo pipefail

PROJECT="asus-screen-toggle"

# ---------- helpers ----------
die() { echo "ERROR: $*" >&2; exit 1; }

require_clean_git() {
    git diff --quiet || die "Working tree is dirty"
    git diff --cached --quiet || die "Index is dirty"
}

get_last_version() {
    git tag --sort=-v:refname | grep '^v' | head -n1 | sed 's/^v//'
}

bump_version() {
    local v=$1 mode=$2
    IFS=. read -r major minor patch <<<"$v"
    case "$mode" in
        patch) patch=$((patch+1)) ;;
        minor) minor=$((minor+1)); patch=0 ;;
        major) major=$((major+1)); minor=0; patch=0 ;;
        *) die "Unknown bump mode: $mode" ;;
    esac
    echo "$major.$minor.$patch"
}

pick_gpg_key() {
    mapfile -t KEYS < <(gpg --list-secret-keys --keyid-format LONG \
        | awk '/^sec/{print $2}' | cut -d/ -f2)

    [[ ${#KEYS[@]} -eq 0 ]] && die "No GPG keys found"

    if [[ ${#KEYS[@]} -eq 1 ]]; then
        echo "${KEYS[0]}"
        return
    fi

    echo "Select GPG key:"
    select k in "${KEYS[@]}"; do
        echo "$k"
        return
    done
}

# ---------- args ----------
MODE=""
VERSION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --patch|--minor|--major) MODE="${1#--}" ;;
        --version) VERSION="$2"; shift ;;
        *) die "Unknown argument $1" ;;
    esac
    shift
done

# ---------- main ----------
require_clean_git

LAST=$(get_last_version)
[[ -z "$LAST" && -z "$VERSION" ]] && die "No previous tag, use --version"

if [[ -z "$VERSION" ]]; then
    [[ -z "$MODE" ]] && die "Use --patch / --minor / --major or --version"
    VERSION=$(bump_version "$LAST" "$MODE")
fi

DEB_VERSION="${VERSION}-1"
TAG="v$VERSION"

echo "Releasing version $VERSION"

git tag "$TAG"

ORIG="../${PROJECT}_${VERSION}.orig.tar.gz"

git archive \
  --format=tar.gz \
  --prefix="${PROJECT}-${VERSION}/" \
  "$TAG" > "$ORIG"

dch -v "$DEB_VERSION"

rm -rf .pc debian/patches/*.rej || true

KEY=$(pick_gpg_key)

dpkg-buildpackage -S -sa "-k$KEY"

dput mentors "../${PROJECT}_${DEB_VERSION}_source.changes"

echo "Release $VERSION uploaded successfully"
