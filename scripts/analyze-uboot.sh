#!/usr/bin/env bash
# Extract and analyze U-Boot bootloader information
#
# Usage: ./scripts/analyze-uboot.sh [firmware.img]
#
# Outputs: output/uboot-version.md
#
# This script extracts:
# - U-Boot version string
# - Build information
# - Environment variables (if accessible)
# - Boot commands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing U-Boot in: $FIRMWARE"

section "Extracting U-Boot version"

# Method 1: Search firmware directly for U-Boot strings
UBOOT_VERSION=""
UBOOT_BUILD=""

# U-Boot version patterns
UBOOT_VERSION=$(strings "$FIRMWARE" 2>/dev/null | grep -E "U-Boot [0-9]+\.[0-9]+" | head -1 || true)

if [[ -z "$UBOOT_VERSION" ]]; then
    # Try extracting from FIT image
    # U-Boot is typically at offset 0x901B4 (FIT start + 0x1000)
    FIT_START=$((0x8F1B4))
    UBOOT_OFFSET=$((FIT_START + 0x1000))
    UBOOT_SIZE=$((0x6d2c0))

    info "Attempting to extract U-Boot from FIT image at offset $UBOOT_OFFSET..."

    # Extract and decompress U-Boot
    UBOOT_STRINGS=$(dd if="$FIRMWARE" bs=1 skip=$UBOOT_OFFSET count=$UBOOT_SIZE 2>/dev/null | \
        gunzip 2>/dev/null | strings 2>/dev/null || true)

    if [[ -n "$UBOOT_STRINGS" ]]; then
        UBOOT_VERSION=$(echo "$UBOOT_STRINGS" | grep -E "U-Boot [0-9]+\.[0-9]+" | head -1 || true)
        UBOOT_BUILD=$(echo "$UBOOT_STRINGS" | grep -E "^\([A-Za-z]+ [A-Za-z]+ [0-9]+" | head -1 || true)
    fi
fi

# Generate output
{
    generate_header "U-Boot Bootloader Analysis" \
        "U-Boot version and configuration extracted from firmware."

    echo "## Version Information"
    echo ""

    if [[ -n "$UBOOT_VERSION" ]]; then
        echo "- **Version:** \`$UBOOT_VERSION\`"
    else
        echo "- **Version:** Could not extract"
    fi

    if [[ -n "$UBOOT_BUILD" ]]; then
        echo "- **Build:** \`$UBOOT_BUILD\`"
    fi

    echo ""

    # Try to extract more details from U-Boot
    echo "## U-Boot Strings Analysis"
    echo ""

    if [[ -n "$UBOOT_STRINGS" ]]; then
        echo "### Boot Commands"
        echo ""
        echo '```'
        echo "$UBOOT_STRINGS" | grep -E "^boot(cmd|args|delay)=" | head -10 || echo "Not found"
        echo '```'
        echo ""

        echo "### Environment Variables"
        echo ""
        echo '```'
        echo "$UBOOT_STRINGS" | grep -E "^[a-z_]+=" | grep -v "^boot" | head -20 || echo "Not found"
        echo '```'
        echo ""

        echo "### Supported Commands"
        echo ""
        echo '```'
        echo "$UBOOT_STRINGS" | grep -E "^(mmc|usb|tftp|nfs|dhcp|ping|md|mw|sf|nand)" | sort -u | head -20 || echo "Not found"
        echo '```'
        echo ""

        echo "### Copyright/License"
        echo ""
        echo '```'
        echo "$UBOOT_STRINGS" | grep -iE "copyright|license|GPL" | head -10 || echo "Not found"
        echo '```'
    else
        echo "*Could not extract U-Boot binary for detailed analysis*"
    fi

    echo ""
    echo "## Methodology"
    echo ""
    echo "U-Boot version was extracted by:"
    echo "1. Searching firmware image for U-Boot version strings"
    echo "2. Extracting gzip-compressed U-Boot from FIT image at offset 0x901B4"
    echo "3. Running \`strings\` on the decompressed binary"

} > "$OUTPUT_DIR/uboot-version.md"

success "Wrote uboot-version.md"
