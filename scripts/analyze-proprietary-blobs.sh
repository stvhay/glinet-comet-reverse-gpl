#!/usr/bin/env bash
# Analyze proprietary/closed-source binaries in firmware
#
# Usage: ./scripts/analyze-proprietary-blobs.sh [firmware.img]
#
# Outputs: output/proprietary-blobs.md
#
# This script identifies:
# - Rockchip proprietary libraries (MPP, RGA, ISP)
# - Vendor-specific binaries
# - Closed-source drivers and blobs
# - Binary analysis (strings, symbols)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk
require_command file

# Get firmware and extract
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing proprietary blobs in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")
ROOTFS=$(find_rootfs "$EXTRACT_DIR")

info "Using rootfs: $ROOTFS"

section "Scanning for proprietary binaries"

# Generate output
{
    generate_header "Proprietary Blobs Inventory" \
        "Closed-source binaries and vendor libraries found in firmware."

    echo "## Rockchip Proprietary Libraries"
    echo ""

    echo "### Media Processing Platform (MPP)"
    echo ""
    echo "| Library | Path | Purpose |"
    echo "|---------|------|---------|"

    # MPP libraries
    for lib in librockchip_mpp.so libmpp.so librk_mpi.so; do
        found=$(find "$ROOTFS" -name "$lib*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            size=$(stat -f%z "$found" 2>/dev/null || stat -c%s "$found" 2>/dev/null || echo "?")
            echo "| $lib | ${found#"$ROOTFS"} | Video codec ($size bytes) |"
        fi
    done

    echo ""

    echo "### Rockchip Graphics Acceleration (RGA)"
    echo ""
    echo "| Library | Path | Purpose |"
    echo "|---------|------|---------|"

    for lib in librga.so librockchip_rga.so; do
        found=$(find "$ROOTFS" -name "$lib*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            size=$(stat -f%z "$found" 2>/dev/null || stat -c%s "$found" 2>/dev/null || echo "?")
            echo "| $lib | ${found#"$ROOTFS"} | 2D graphics ($size bytes) |"
        fi
    done

    echo ""

    echo "### ISP (Image Signal Processor)"
    echo ""
    echo "| Library | Path | Purpose |"
    echo "|---------|------|---------|"

    for lib in librkaiq.so librkisp.so librk_aiq.so; do
        found=$(find "$ROOTFS" -name "$lib*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            size=$(stat -f%z "$found" 2>/dev/null || stat -c%s "$found" 2>/dev/null || echo "?")
            echo "| $lib | ${found#"$ROOTFS"} | Camera ISP ($size bytes) |"
        fi
    done

    echo ""

    echo "### Neural Processing Unit (NPU)"
    echo ""
    echo "| Library | Path | Purpose |"
    echo "|---------|------|---------|"

    for lib in librknn_runtime.so librknnrt.so; do
        found=$(find "$ROOTFS" -name "$lib*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            size=$(stat -f%z "$found" 2>/dev/null || stat -c%s "$found" 2>/dev/null || echo "?")
            echo "| $lib | ${found#"$ROOTFS"} | AI inference ($size bytes) |"
        fi
    done

    echo ""

    # Scan for all Rockchip libraries
    echo "## All Rockchip Libraries"
    echo ""
    echo '```'
    find "$ROOTFS" -name "librockchip*" -o -name "librk*" -o -name "*rga*" -o -name "*mpp*" 2>/dev/null | \
        grep -v ".pyc" | sort -u | while read -r lib; do
        echo "${lib#"$ROOTFS"}"
    done || echo "None found"
    echo '```'
    echo ""

    # Check for other vendor blobs
    echo "## Other Vendor Libraries"
    echo ""

    echo "### WiFi/Bluetooth"
    echo ""
    echo "| File | Path | Type |"
    echo "|------|------|------|"

    # Broadcom/Cypress WiFi
    for blob in bcmdhd*.ko fw_bcm*.bin nvram*.txt brcmfmac*.bin; do
        found=$(find "$ROOTFS" -name "$blob" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            ftype=$(file -b "$found" 2>/dev/null | cut -d, -f1 || echo "unknown")
            echo "| $blob | ${found#"$ROOTFS"} | $ftype |"
        fi
    done

    # Realtek WiFi
    for blob in rtl*.bin rtl*.ko; do
        found=$(find "$ROOTFS" -name "$blob" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            ftype=$(file -b "$found" 2>/dev/null | cut -d, -f1 || echo "unknown")
            echo "| $blob | ${found#"$ROOTFS"} | $ftype |"
        fi
    done

    echo ""

    # Firmware blobs
    echo "## Firmware Blobs (/lib/firmware)"
    echo ""
    if [[ -d "$ROOTFS/lib/firmware" ]]; then
        echo '```'
        find "$ROOTFS/lib/firmware" -type f 2>/dev/null | while read -r fw; do
            size=$(stat -f%z "$fw" 2>/dev/null || stat -c%s "$fw" 2>/dev/null || echo "?")
            echo "${fw#"$ROOTFS"} ($size bytes)"
        done | head -50 || echo "None found"
        echo '```'
    else
        echo "No /lib/firmware directory found."
    fi
    echo ""

    # Kernel modules (out-of-tree)
    echo "## Kernel Modules"
    echo ""
    echo "Potentially proprietary kernel modules:"
    echo ""
    echo "| Module | Path | Size |"
    echo "|--------|------|------|"

    find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | while read -r ko; do
        name=$(basename "$ko")
        size=$(stat -f%z "$ko" 2>/dev/null || stat -c%s "$ko" 2>/dev/null || echo "?")
        # Check if it's likely proprietary (no GPL string)
        if ! strings "$ko" 2>/dev/null | grep -qi "GPL"; then
            echo "| $name | ${ko#"$ROOTFS"} | $size bytes (no GPL) |"
        fi
    done | head -30

    echo ""

    # Binary analysis of key proprietary files
    echo "## Binary Analysis"
    echo ""

    # Analyze a key proprietary binary if found
    mpp_lib=$(find "$ROOTFS" -name "librockchip_mpp.so*" -type f 2>/dev/null | head -1 || true)
    if [[ -n "$mpp_lib" ]]; then
        echo "### librockchip_mpp.so"
        echo ""
        echo "**File info:**"
        echo '```'
        file "$mpp_lib" 2>/dev/null || echo "Could not determine file type"
        echo '```'
        echo ""

        echo "**Interesting strings:**"
        echo '```'
        strings "$mpp_lib" 2>/dev/null | grep -iE "copyright|version|rockchip|license|build" | head -20 || echo "No relevant strings found"
        echo '```'
        echo ""
    fi

    # Summary
    echo "## Summary"
    echo ""

    rk_count=$(find "$ROOTFS" -name "librockchip*" -o -name "librk*" 2>/dev/null | wc -l | tr -d ' ')
    fw_count=$(find "$ROOTFS/lib/firmware" -type f 2>/dev/null | wc -l | tr -d ' ' || echo "0")
    ko_count=$(find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | wc -l | tr -d ' ')

    echo "| Category | Count |"
    echo "|----------|-------|"
    echo "| Rockchip libraries | $rk_count |"
    echo "| Firmware blobs | $fw_count |"
    echo "| Kernel modules | $ko_count |"

} > "$OUTPUT_DIR/proprietary-blobs.md"

success "Wrote proprietary-blobs.md"
