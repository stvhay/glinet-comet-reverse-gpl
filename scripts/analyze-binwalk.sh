#!/usr/bin/env bash
# Analyze firmware structure using binwalk
#
# Usage: ./scripts/analyze-binwalk.sh [firmware.img]
#
# Outputs: output/binwalk-scan.md
#
# This script performs a binwalk scan of the firmware image to identify
# embedded files, compression, and partition structure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
FIRMWARE_FILE=$(basename "$FIRMWARE")
info "Analyzing: $FIRMWARE"

# Run binwalk scan
section "Binwalk Signature Scan"
BINWALK_OUTPUT=$(binwalk "$FIRMWARE" 2>/dev/null || true)

# Generate output
{
    generate_header "Binwalk Firmware Analysis" \
        "Signature scan of firmware image to identify embedded components."

    echo "## Firmware File"
    echo ""
    echo "- **Filename:** \`$FIRMWARE_FILE\`"
    echo "- **Size:** $(stat -f%z "$FIRMWARE" 2>/dev/null || stat -c%s "$FIRMWARE") bytes"
    echo ""

    echo "## Binwalk Signature Scan"
    echo ""
    echo '```'
    # Strip the temp work directory path from output
    echo "${BINWALK_OUTPUT//$WORK_DIR\//}"
    echo '```'
    echo ""

    echo "## Identified Components"
    echo ""
    echo "| Offset | Type | Description |"
    echo "|--------|------|-------------|"

    # Parse binwalk output into table
    # Binwalk output format: DECIMAL  HEXADECIMAL  DESCRIPTION
    # Skip header lines (those starting with DECIMAL or dashes)
    echo "$BINWALK_OUTPUT" | while read -r line; do
        # Only process lines that start with a number (data lines)
        if [[ "$line" =~ ^[0-9]+ ]]; then
            # Extract fields using awk: hex offset is $2, description is $3 onwards
            hex=$(echo "$line" | awk '{print $2}')
            desc=$(echo "$line" | awk '{$1=$2=""; print substr($0,3)}')
            type=$(echo "$desc" | awk '{print $1}')
            # Skip continuation lines (those with partial data)
            if [[ -n "$hex" && "$hex" =~ ^0x ]]; then
                echo "| $hex | $type | $desc |"
            fi
        fi
    done

    echo ""
    echo "## Key Findings"
    echo ""

    # Count component types
    squashfs_count=$(echo "$BINWALK_OUTPUT" | grep -ci "squashfs" || echo "0")
    gzip_count=$(echo "$BINWALK_OUTPUT" | grep -ci "gzip" || echo "0")
    dtb_count=$(echo "$BINWALK_OUTPUT" | grep -ci "device tree\|dtb\|flattened" || echo "0")
    ext4_count=$(echo "$BINWALK_OUTPUT" | grep -ci "ext.*filesystem" || echo "0")

    echo "- **SquashFS filesystems:** $squashfs_count"
    echo "- **Gzip compressed data:** $gzip_count"
    echo "- **Device Tree Blobs:** $dtb_count"
    echo "- **EXT4 filesystems:** $ext4_count"

} > "$OUTPUT_DIR/binwalk-scan.md"

success "Wrote binwalk-scan.md"

# ==============================================================================
# Generate offsets artifact file for use by other scripts
# ==============================================================================
section "Extracting firmware offsets"

{
    echo "# Firmware offsets extracted from binwalk analysis"
    echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# Source: $FIRMWARE_FILE"
    echo "#"
    echo "# These values are parsed from binwalk output and should be used"
    echo "# by other analysis scripts instead of hardcoding offsets."
    echo ""

    # Extract bootloader FIT offset (first device tree blob)
    bootloader_fit=$(echo "$BINWALK_OUTPUT" | grep -i "device tree blob" | head -1 | awk '{print $1}')
    if [[ -n "$bootloader_fit" ]]; then
        echo "# Bootloader FIT image (contains U-Boot + OP-TEE)"
        printf 'BOOTLOADER_FIT_OFFSET=0x%X\n' "$bootloader_fit"
        printf 'BOOTLOADER_FIT_OFFSET_DEC=%d\n' "$bootloader_fit"
    fi
    echo ""

    # Extract U-Boot gzip offset
    uboot_gz=$(echo "$BINWALK_OUTPUT" | grep -i "u-boot-nodtb.bin" | head -1 | awk '{print $1}')
    if [[ -n "$uboot_gz" ]]; then
        echo "# U-Boot binary (gzip compressed)"
        printf 'UBOOT_GZ_OFFSET=0x%X\n' "$uboot_gz"
        printf 'UBOOT_GZ_OFFSET_DEC=%d\n' "$uboot_gz"
    fi
    echo ""

    # Extract OP-TEE gzip offset
    optee_gz=$(echo "$BINWALK_OUTPUT" | grep -i "tee.bin" | head -1 | awk '{print $1}')
    if [[ -n "$optee_gz" ]]; then
        echo "# OP-TEE binary (gzip compressed)"
        printf 'OPTEE_GZ_OFFSET=0x%X\n' "$optee_gz"
        printf 'OPTEE_GZ_OFFSET_DEC=%d\n' "$optee_gz"
    fi
    echo ""

    # Extract kernel FIT offset (larger DTB after bootloader)
    # The kernel FIT is typically the DTB around 4-5MB offset with ~96KB size
    kernel_fit=$(echo "$BINWALK_OUTPUT" | grep -i "device tree blob" | grep "96558 bytes" | head -1 | awk '{print $1}')
    if [[ -z "$kernel_fit" ]]; then
        # Fallback: look for DTB after 4MB
        kernel_fit=$(echo "$BINWALK_OUTPUT" | grep -i "device tree blob" | awk '$1 > 4000000 {print $1; exit}')
    fi
    if [[ -n "$kernel_fit" ]]; then
        echo "# Kernel FIT image (contains kernel + DTB)"
        printf 'KERNEL_FIT_OFFSET=0x%X\n' "$kernel_fit"
        printf 'KERNEL_FIT_OFFSET_DEC=%d\n' "$kernel_fit"
    fi
    echo ""

    # Extract rootfs.cpio offset
    rootfs_cpio=$(echo "$BINWALK_OUTPUT" | grep -i "rootfs.cpio" | head -1 | awk '{print $1}')
    if [[ -n "$rootfs_cpio" ]]; then
        echo "# Root filesystem CPIO archive"
        printf 'ROOTFS_CPIO_OFFSET=0x%X\n' "$rootfs_cpio"
        printf 'ROOTFS_CPIO_OFFSET_DEC=%d\n' "$rootfs_cpio"
    fi
    echo ""

    # Extract SquashFS offset
    squashfs=$(echo "$BINWALK_OUTPUT" | grep -i "squashfs" | head -1 | awk '{print $1}')
    if [[ -n "$squashfs" ]]; then
        echo "# SquashFS filesystem (main rootfs)"
        printf 'SQUASHFS_OFFSET=0x%X\n' "$squashfs"
        printf 'SQUASHFS_OFFSET_DEC=%d\n' "$squashfs"
        # Also extract size if available
        squashfs_size=$(echo "$BINWALK_OUTPUT" | grep -i "squashfs" | head -1 | grep -oE "image size: [0-9]+" | grep -oE "[0-9]+")
        if [[ -n "$squashfs_size" ]]; then
            printf 'SQUASHFS_SIZE=%d\n' "$squashfs_size"
        fi
    fi
    echo ""

    # Extract EXT filesystem offsets
    ext_count=0
    echo "$BINWALK_OUTPUT" | grep -i "ext.*filesystem" | while read -r line; do
        offset=$(echo "$line" | awk '{print $1}')
        ext_count=$((ext_count + 1))
        printf '# EXT filesystem %d\n' "$ext_count"
        printf 'EXT%d_OFFSET=0x%X\n' "$ext_count" "$offset"
        printf 'EXT%d_OFFSET_DEC=%d\n' "$ext_count" "$offset"
    done

} > "$OUTPUT_DIR/binwalk-offsets.sh"

success "Wrote binwalk-offsets.sh (firmware offset artifacts)"
