#!/usr/bin/env bash
# Analyze Secure Boot Configuration
#
# Usage: ./scripts/analyze-secure-boot.sh [firmware.img]
#
# Outputs: output/secure-boot-analysis.md
#
# This script extracts and analyzes secure boot related information from the firmware.
# Requires: nix develop shell (provides binwalk, dtc, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk
require_command strings

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing secure boot in: $FIRMWARE"

# Extract firmware if needed
EXTRACT_DIR=$(extract_firmware "$FIRMWARE")

# Load offsets from binwalk analysis artifact
load_firmware_offsets

section "Analyzing secure boot configuration"

# Convert offsets to directory names (binwalk uses uppercase hex)
BOOTLOADER_DIR=$(printf "%X" "$BOOTLOADER_FIT_OFFSET_DEC")
KERNEL_DIR=$(printf "%X" "$KERNEL_FIT_OFFSET_DEC")

# Find DTS files
BOOTLOADER_FIT="$EXTRACT_DIR/$BOOTLOADER_DIR/system.dtb"
KERNEL_FIT="$EXTRACT_DIR/$KERNEL_DIR/system.dtb"

# Find the largest kernel DTS for full device tree
KERNEL_FULL_DTS=$(find "$EXTRACT_DIR" -name "system.dtb" -type f -print0 2>/dev/null | xargs -0 ls -S 2>/dev/null | head -1 || true)

# Generate output
{
    generate_header "Secure Boot Analysis" \
        "Analysis of secure boot configuration based on static examination of firmware binaries."

    echo "## Overview"
    echo ""
    echo "This document analyzes the secure boot configuration of the GL.iNet Comet firmware."
    echo ""

    # ==============================================================================
    # Section 1: FIT Image Signature Analysis
    # ==============================================================================
    echo "## FIT Image Signatures"
    echo ""
    echo "FIT (Flattened Image Tree) images can contain RSA signatures for verified boot."
    echo ""

    echo "### Bootloader FIT Image"
    echo ""
    echo "Extracted from firmware offset \`$BOOTLOADER_FIT_OFFSET\`:"
    echo ""

    if [[ -f "$BOOTLOADER_FIT" ]]; then
        echo '```'
        grep -A 30 "configurations" "$BOOTLOADER_FIT" 2>/dev/null | head -40 || echo "Could not extract configuration"
        echo '```'
    else
        echo "*Bootloader FIT DTS not available*"
    fi
    echo ""

    echo "### Kernel FIT Image"
    echo ""
    echo "Extracted from firmware offset \`$KERNEL_FIT_OFFSET\`:"
    echo ""

    if [[ -f "$KERNEL_FIT" ]]; then
        echo '```'
        grep -A 30 "configurations" "$KERNEL_FIT" 2>/dev/null | head -40 || echo "Could not extract configuration"
        echo '```'
    else
        echo "*Kernel FIT DTS not available*"
    fi
    echo ""

    echo "### Signature Summary"
    echo ""
    echo "| FIT Image | Signature Algorithm | Key Name | Signed Components |"
    echo "|-----------|---------------------|----------|-------------------|"

    # Extract signature info from FIT images
    if [[ -f "$BOOTLOADER_FIT" ]]; then
        ALGO=$(grep -oP 'algo = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | grep rsa | head -1 || echo "unknown")
        KEY=$(grep -oP 'key-name-hint = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | head -1 || echo "unknown")
        SIGNED=$(grep -oP 'sign-images = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | head -1 || echo "unknown")
        echo "| Bootloader (uboot+optee) | $ALGO | $KEY | $SIGNED |"
    fi

    if [[ -f "$KERNEL_FIT" ]]; then
        ALGO=$(grep -oP 'algo = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | grep rsa | head -1 || echo "unknown")
        KEY=$(grep -oP 'key-name-hint = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | head -1 || echo "unknown")
        SIGNED=$(grep -oP 'sign-images = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | head -1 || echo "unknown")
        echo "| Kernel | $ALGO | $KEY | $SIGNED |"
    fi
    echo ""

    # ==============================================================================
    # Section 2: U-Boot Secure Boot Strings
    # ==============================================================================
    echo "## U-Boot Secure Boot Analysis"
    echo ""
    echo "U-Boot binary extracted and decompressed from bootloader FIT image."
    echo ""
    echo "### Verification-Related Strings"
    echo ""

    # Extract U-Boot from gzip offset
    UBOOT_STRINGS=""
    if [[ -n "${UBOOT_GZ_OFFSET_DEC:-}" ]]; then
        UBOOT_STRINGS=$(dd if="$FIRMWARE" bs=1 skip="$UBOOT_GZ_OFFSET_DEC" count=500000 2>/dev/null | \
            gunzip 2>/dev/null | strings 2>/dev/null || true)
    fi

    echo '```'
    if [[ -n "$UBOOT_STRINGS" ]]; then
        echo "$UBOOT_STRINGS" | \
            grep -iE 'verified|signature|secure.?boot|FIT.*sign|required|rsa.*verify' | \
            sort -u | head -30 || echo "No verification strings found"
    else
        echo "Could not extract U-Boot strings"
    fi
    echo '```'
    echo ""

    echo "### Key Findings in U-Boot"
    echo ""
    echo '```'
    if [[ -n "$UBOOT_STRINGS" ]]; then
        echo "$UBOOT_STRINGS" | \
            grep -E "FIT:.*signed|Verified-boot:|Can't read verified-boot|CONFIG_FIT_SIGNATURE" | \
            sort -u || echo "No key findings"
    fi
    echo '```'
    echo ""

    # ==============================================================================
    # Section 3: OP-TEE Secure Boot Strings
    # ==============================================================================
    echo "## OP-TEE Analysis"
    echo ""
    echo "OP-TEE (Trusted Execution Environment) handles secure boot flag storage."
    echo ""
    echo "### Secure Boot Flag Functions"
    echo ""

    # Extract OP-TEE from gzip offset
    OPTEE_STRINGS=""
    if [[ -n "${OPTEE_GZ_OFFSET_DEC:-}" ]]; then
        OPTEE_STRINGS=$(dd if="$FIRMWARE" bs=1 skip="$OPTEE_GZ_OFFSET_DEC" count=300000 2>/dev/null | \
            gunzip 2>/dev/null | strings 2>/dev/null || true)
    fi

    echo '```'
    if [[ -n "$OPTEE_STRINGS" ]]; then
        echo "$OPTEE_STRINGS" | \
            grep -iE 'secure.?boot|otp.*key|set.*flag|key.*index|enable.*flag' | \
            sort -u | head -30 || echo "No secure boot functions found"
    else
        echo "Could not extract OP-TEE strings"
    fi
    echo '```'
    echo ""

    # ==============================================================================
    # Section 4: Device Tree OTP/Crypto Analysis
    # ==============================================================================
    echo "## Device Tree Analysis"
    echo ""
    echo "### OTP (One-Time Programmable) Memory"
    echo ""

    if [[ -n "$KERNEL_FULL_DTS" && -f "$KERNEL_FULL_DTS" ]]; then
        echo '```'
        grep -A 10 "otp@" "$KERNEL_FULL_DTS" 2>/dev/null | head -20 || echo "No OTP node found"
        echo '```'
        echo ""

        echo "### Crypto Engine"
        echo ""
        echo '```'
        grep -A 10 "crypto@" "$KERNEL_FULL_DTS" 2>/dev/null | head -20 || echo "No crypto node found"
        echo '```'
    else
        echo "*Device tree not available for analysis*"
    fi

} > "$OUTPUT_DIR/secure-boot-analysis.md"

success "Wrote secure-boot-analysis.md"
