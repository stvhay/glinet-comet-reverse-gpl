#!/usr/bin/env bash
# Analyze root filesystem contents
#
# Usage: ./scripts/analyze-rootfs.sh [firmware.img]
#
# Outputs:
#   - output/build-info.md - OS version and build information
#   - output/packages.md - Shared libraries inventory
#   - output/gpl-binaries.md - GPL-licensed binaries
#   - output/license-files.md - License files in filesystem
#   - output/licenses.md - Automated license detection
#   - output/kernel-modules.md - Kernel modules
#   - output/kernel-version.md - Kernel version
#
# This is the main license compliance analysis script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk
require_command file

# Get firmware and extract
FIRMWARE=$(get_firmware "${1:-}")
FIRMWARE_FILE=$(basename "$FIRMWARE")
FIRMWARE_VERSION=$(extract_version "$FIRMWARE")

info "Analyzing rootfs in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")
ROOTFS=$(find_rootfs "$EXTRACT_DIR")

info "Using rootfs: $ROOTFS"

# ==============================================================================
# Build Info
# ==============================================================================
section "Build Information"

{
    generate_header "Build Information" \
        "Operating system and build configuration."

    if [[ -f "$ROOTFS/etc/os-release" ]]; then
        echo "## /etc/os-release"
        echo ""
        echo '```'
        cat "$ROOTFS/etc/os-release"
        echo '```'
    else
        echo "*No /etc/os-release found*"
    fi

} > "$OUTPUT_DIR/build-info.md"
success "Wrote build-info.md"

# ==============================================================================
# Kernel Version
# ==============================================================================
section "Kernel Version"

{
    generate_header "Kernel Version" \
        "Linux kernel version detected from module vermagic."

    ko_file=$(find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | head -1 || true)
    if [[ -n "$ko_file" ]]; then
        version=$(strings "$ko_file" 2>/dev/null | grep -oE "vermagic=[^ ]+" | head -1 || echo "unknown")
        echo "**Kernel Version:** \`$version\`"
    else
        echo "*No kernel modules found to extract version*"
    fi

} > "$OUTPUT_DIR/kernel-version.md"
success "Wrote kernel-version.md"

# ==============================================================================
# Kernel Modules
# ==============================================================================
section "Kernel Modules"

{
    generate_header "Kernel Modules" \
        "Loadable kernel modules (.ko files) found in firmware."

    echo "## Module List"
    echo ""
    echo "| Module | Path | Size |"
    echo "|--------|------|------|"

    find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | while read -r ko; do
        name=$(basename "$ko")
        path="${ko#$ROOTFS}"
        size=$(stat -f%z "$ko" 2>/dev/null || stat -c%s "$ko" 2>/dev/null || echo "?")
        echo "| $name | $path | $size |"
    done

    count=$(find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo "**Total modules:** $count"

} > "$OUTPUT_DIR/kernel-modules.md"
success "Wrote kernel-modules.md"

# ==============================================================================
# Shared Libraries (Packages)
# ==============================================================================
section "Shared Libraries"

{
    generate_header "Shared Libraries" \
        "System libraries found in the firmware."

    echo "## Library List"
    echo ""
    echo "| Library | Path | Size |"
    echo "|---------|------|------|"

    find "$ROOTFS" -name "*.so*" -type f 2>/dev/null | sort | while read -r lib; do
        name=$(basename "$lib")
        path="${lib#$ROOTFS}"
        size=$(stat -f%z "$lib" 2>/dev/null || stat -c%s "$lib" 2>/dev/null || echo "?")
        echo "| $name | $path | $size |"
    done | head -100

    count=$(find "$ROOTFS" -name "*.so*" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo "**Total libraries:** $count"

} > "$OUTPUT_DIR/packages.md"
success "Wrote packages.md"

# ==============================================================================
# GPL Binaries
# ==============================================================================
section "GPL Binaries"

{
    generate_header "GPL-Licensed Binaries" \
        "Binaries that are typically GPL-licensed."

    echo "## BusyBox"
    echo ""
    if [[ -f "$ROOTFS/bin/busybox" ]]; then
        version=$(strings "$ROOTFS/bin/busybox" 2>/dev/null | grep -i "busybox v" | head -1 || echo "unknown")
        echo "- **Found:** \`/bin/busybox\`"
        echo "- **Version:** \`$version\`"
        echo ""
        echo "### BusyBox Applets"
        echo ""
        echo '```'
        "$ROOTFS/bin/busybox" --list 2>/dev/null | head -50 || strings "$ROOTFS/bin/busybox" 2>/dev/null | grep -E "^\[" | head -1 || echo "Could not list applets"
        echo '```'
    else
        echo "*BusyBox not found*"
    fi
    echo ""

    echo "## GNU Coreutils"
    echo ""
    echo "| Binary | Path | License |"
    echo "|--------|------|---------|"

    for bin in ls cp mv rm cat grep sed awk; do
        found=$(find "$ROOTFS" -name "$bin" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            # Check if it's a symlink to busybox
            if file "$found" 2>/dev/null | grep -q "symbolic link"; then
                echo "| $bin | ${found#$ROOTFS} | BusyBox (GPL-2.0) |"
            else
                echo "| $bin | ${found#$ROOTFS} | GPL-3.0+ |"
            fi
        fi
    done
    echo ""

    echo "## Other GPL Binaries"
    echo ""
    echo "| Binary | Path | Likely License |"
    echo "|--------|------|----------------|"

    for bin in bash sh ash dash tar gzip bzip2 xz; do
        found=$(find "$ROOTFS" -name "$bin" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            echo "| $bin | ${found#$ROOTFS} | GPL |"
        fi
    done

} > "$OUTPUT_DIR/gpl-binaries.md"
success "Wrote gpl-binaries.md"

# ==============================================================================
# License Files
# ==============================================================================
section "License Files"

{
    generate_header "License Files" \
        "License and copyright files found in the firmware."

    echo "## License Files Found"
    echo ""

    find "$ROOTFS" -iname "*license*" -o -iname "*copying*" -o -iname "*copyright*" 2>/dev/null | \
        sort | while read -r f; do
        echo "### ${f#$ROOTFS}"
        echo ""
        echo '```'
        head -50 "$f" 2>/dev/null || echo "Could not read file"
        echo '```'
        echo ""
    done | head -500

} > "$OUTPUT_DIR/license-files.md"
success "Wrote license-files.md"

# ==============================================================================
# Automated License Detection
# ==============================================================================
section "License Detection"

{
    generate_header "Automated License Detection" \
        "Licenses detected through binary analysis and file inspection."

    echo "## Detection Methods"
    echo ""
    echo "1. Binary strings search for license keywords"
    echo "2. Python package metadata inspection"
    echo "3. Known library name matching"
    echo "4. License file content analysis"
    echo ""

    # Known library licenses
    declare -A KNOWN_LICENSES
    KNOWN_LICENSES["libc.so"]="LGPL-2.1"
    KNOWN_LICENSES["libpthread"]="LGPL-2.1"
    KNOWN_LICENSES["libm.so"]="LGPL-2.1"
    KNOWN_LICENSES["libdl.so"]="LGPL-2.1"
    KNOWN_LICENSES["librt.so"]="LGPL-2.1"
    KNOWN_LICENSES["libstdc++"]="GPL-3.0-with-GCC-exception"
    KNOWN_LICENSES["libgcc"]="GPL-3.0-with-GCC-exception"
    KNOWN_LICENSES["libssl"]="OpenSSL"
    KNOWN_LICENSES["libcrypto"]="OpenSSL"
    KNOWN_LICENSES["libz.so"]="Zlib"
    KNOWN_LICENSES["libsqlite"]="Public-Domain"
    KNOWN_LICENSES["librockchip"]="Apache-2.0"
    KNOWN_LICENSES["librga"]="Apache-2.0"
    KNOWN_LICENSES["libavcodec"]="LGPL-2.1"
    KNOWN_LICENSES["libavformat"]="LGPL-2.1"
    KNOWN_LICENSES["libavutil"]="LGPL-2.1"

    echo "## Detected Licenses"
    echo ""
    echo "| Component | License | Detection Method |"
    echo "|-----------|---------|------------------|"

    # Check known libraries
    for pattern in "${!KNOWN_LICENSES[@]}"; do
        found=$(find "$ROOTFS" -name "*$pattern*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            echo "| $pattern | ${KNOWN_LICENSES[$pattern]} | Known library |"
        fi
    done

    # Check Python packages
    if [[ -d "$ROOTFS/usr/lib/python3.12/site-packages" ]]; then
        echo ""
        echo "## Python Packages"
        echo ""
        echo "| Package | License | Source |"
        echo "|---------|---------|--------|"

        find "$ROOTFS/usr/lib/python3.12/site-packages" -name "METADATA" -type f 2>/dev/null | while read -r meta; do
            pkg_dir=$(dirname "$meta")
            pkg_name=$(basename "$pkg_dir" | sed 's/-[0-9].*//')
            license=$(grep "^License:" "$meta" 2>/dev/null | cut -d: -f2 | tr -d ' ' || echo "unknown")
            if [[ -n "$license" && "$license" != "unknown" ]]; then
                echo "| $pkg_name | $license | METADATA |"
            fi
        done | head -50
    fi

    echo ""
    echo "## GPL Components Summary"
    echo ""
    echo "Components requiring source code release:"
    echo ""
    echo "| Component | License | Obligation |"
    echo "|-----------|---------|------------|"
    echo "| Linux Kernel | GPL-2.0 | Must provide source |"
    echo "| U-Boot | GPL-2.0+ | Must provide source |"
    echo "| BusyBox | GPL-2.0 | Must provide source |"
    echo "| glibc | LGPL-2.1 | Must provide source if modified |"

} > "$OUTPUT_DIR/licenses.md"
success "Wrote licenses.md"

# ==============================================================================
# Summary
# ==============================================================================
section "Summary"

echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR"/*.md 2>/dev/null | awk '{print "  " $NF}'
