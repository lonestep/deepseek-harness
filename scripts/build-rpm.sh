#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE="$ROOT_DIR/scripts/rpm/deepseek-harness.spec"
RPMBUILD_DIR="/tmp/rpmbuild-dsh"
OUTPUT_DIR="$ROOT_DIR/dist/rpm"

TARGET="${1:-universal}"

HOST_DIST="el10"
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    MAJOR_VER="${VERSION_ID%%.*}"
    if [ -n "$MAJOR_VER" ]; then
        HOST_DIST="el${MAJOR_VER}"
    fi
fi

case "$TARGET" in
    universal|unified|el)
        DISTS=("el")
        ;;
    all|both)
        DISTS=("el" "el9" "el10")
        ;;
    auto)
        DISTS=("$HOST_DIST")
        ;;
    el9|el10)
        DISTS=("$TARGET")
        ;;
    *)
        echo "Usage: $0 [universal|all|auto|el9|el10]" >&2
        exit 1
        ;;
esac

mkdir -p "$OUTPUT_DIR"

for dist_tag in "${DISTS[@]}"; do
    echo "==> Building RPM for $dist_tag..."
    rm -rf "$RPMBUILD_DIR"
    mkdir -p "$RPMBUILD_DIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
    cp "$SPEC_FILE" "$RPMBUILD_DIR/SPECS/"

    rpmbuild \
        --define "_topdir $RPMBUILD_DIR" \
        --define "_sourcedir $ROOT_DIR" \
        --define "dist .$dist_tag" \
        -bb "$RPMBUILD_DIR/SPECS/deepseek-harness.spec"

    cp -f "$RPMBUILD_DIR"/RPMS/*/*.rpm "$OUTPUT_DIR/"
done

echo "==> RPM build complete: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/*.rpm
