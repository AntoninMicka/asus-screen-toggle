#!/usr/bin/env bash
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }

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

git diff --quiet || die "Working tree not clean"

LAST=$(git tag --sort=-v:refname | grep '^v' | head -n1 | sed 's/^v//')

if [[ -z "$VERSION" ]]; then
  [[ -z "$MODE" ]] && die "Use --patch / --minor / --major or --version"
  IFS=. read -r M m p <<<"$LAST"
  case "$MODE" in
    patch) p=$((p+1)) ;;
    minor) m=$((m+1)); p=0 ;;
    major) M=$((M+1)); m=0; p=0 ;;
  esac
  VERSION="$M.$m.$p"
fi

DEB_VERSION="$VERSION-1"

echo "Releasing $VERSION"

dch -v "$DEB_VERSION"
git commit -am "Release $VERSION"

git tag "v$VERSION"
git push origin main --tags

echo "Tag v$VERSION pushed – GitHub CI will validate the source."
