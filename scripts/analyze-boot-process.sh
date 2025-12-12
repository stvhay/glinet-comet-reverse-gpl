#!/usr/bin/env bash
# Analyze boot process and partition layout
#
# Usage: ./scripts/analyze-boot-process.sh [firmware.img]
#
# Outputs: output/boot-process.md
#
# This script documents:
# - Boot chain (BROM -> SPL -> OP-TEE -> U-Boot -> Kernel)
# - Partition layout
# - FIT image structure
# - A/B slot configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing boot process in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")

# Load offsets from binwalk analysis artifact
load_firmware_offsets

section "Analyzing boot chain"

# Convert hex offsets to directory names (binwalk uses uppercase hex without 0x prefix)
BOOTLOADER_DIR=$(printf "%X" "$BOOTLOADER_FIT_OFFSET_DEC")
KERNEL_DIR=$(printf "%X" "$KERNEL_FIT_OFFSET_DEC")

# Get DTS files if available
BOOTLOADER_DTS="$EXTRACT_DIR/$BOOTLOADER_DIR/system.dtb"
KERNEL_DTS="$EXTRACT_DIR/$KERNEL_DIR/system.dtb"

# Extract information from FIT images
get_fit_info() {
    local dts_file="$1"
    if [[ -f "$dts_file" ]]; then
        cat "$dts_file" 2>/dev/null
    fi
}

BOOTLOADER_FIT_INFO=$(get_fit_info "$BOOTLOADER_DTS")
KERNEL_FIT_INFO=$(get_fit_info "$KERNEL_DTS")

# Extract U-Boot version
UBOOT_VERSION=$(strings "$FIRMWARE" 2>/dev/null | grep -E "U-Boot [0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "unknown")

# Extract kernel version from modules
ROOTFS=$(find_rootfs "$EXTRACT_DIR" 2>/dev/null || true)
KERNEL_VERSION="unknown"
if [[ -n "$ROOTFS" ]]; then
    ko_file=$(find "$ROOTFS" -name "*.ko" -type f 2>/dev/null | head -1 || true)
    if [[ -n "$ko_file" ]]; then
        KERNEL_VERSION=$(strings "$ko_file" 2>/dev/null | grep -oE "vermagic=[0-9]+\.[0-9]+\.[0-9]+" | head -1 | cut -d= -f2 || echo "unknown")
    fi
fi

# Generate output
{
    generate_header "Boot Process and Partition Layout" \
        "Analysis of the GL.iNet Comet boot chain and storage layout."

    echo "## Hardware Platform"
    echo ""
    echo "| Property | Value | Source |"
    echo "|----------|-------|--------|"

    # Extract platform info from device tree
    # Look for the largest DTS which contains full device tree
    KERNEL_FULL_DTS=$(find "$EXTRACT_DIR" -name "system.dtb" -type f -print0 2>/dev/null | xargs -0 ls -S 2>/dev/null | head -1 || true)
    if [[ -n "$KERNEL_FULL_DTS" && -f "$KERNEL_FULL_DTS" ]]; then
        compat=$(grep -oP 'compatible = "\K[^"]+' "$KERNEL_FULL_DTS" 2>/dev/null | head -1 || true)
        if [[ -n "$compat" ]]; then
            echo "| Device Tree Compatible | \`$compat\` | DTS |"
            # Derive SoC from compatible string
            if [[ "$compat" == *"rv1126"* ]]; then
                echo "| SoC | Rockchip RV1126 | DTS compatible |"
            fi
        fi
    fi

    # Derive architecture from ELF binaries in rootfs
    if [[ -n "$ROOTFS" ]]; then
        elf_sample=$(find "$ROOTFS" -type f -executable 2>/dev/null | head -1 || true)
        if [[ -n "$elf_sample" ]]; then
            arch=$(file "$elf_sample" 2>/dev/null | grep -oE "ARM|x86-64|aarch64" | head -1 || true)
            [[ -n "$arch" ]] && echo "| Architecture | $arch | ELF header |"
        fi
    fi
    echo ""

    echo "## Boot Chain"
    echo ""
    echo "See [docs/reference/rockchip-boot-chain.md](../docs/reference/rockchip-boot-chain.md)"
    echo "for the standard Rockchip RV1126 boot sequence."
    echo ""
    echo "Components found in this firmware:"
    echo ""
    echo "| Stage | Found | Evidence |"
    echo "|-------|-------|----------|"

    # Check for OP-TEE in extracted files
    if find "$EXTRACT_DIR" -name "tee.bin" -type f 2>/dev/null | grep -q .; then
        echo "| OP-TEE | ✅ | tee.bin found in extraction |"
    else
        echo "| OP-TEE | ❓ | tee.bin not found |"
    fi

    # Check for U-Boot
    if find "$EXTRACT_DIR" -name "u-boot*" -type f 2>/dev/null | grep -q .; then
        echo "| U-Boot | ✅ | u-boot binary found in extraction |"
    elif strings "$FIRMWARE" 2>/dev/null | grep -q "U-Boot"; then
        echo "| U-Boot | ✅ | U-Boot strings found in firmware |"
    else
        echo "| U-Boot | ❓ | U-Boot not identified |"
    fi

    # Check for kernel FIT
    if [[ -n "${KERNEL_FIT_OFFSET:-}" ]]; then
        echo "| Kernel | ✅ | FIT image at offset \`$KERNEL_FIT_OFFSET\` |"
    else
        echo "| Kernel | ❓ | Kernel FIT not identified |"
    fi

    # Check for initramfs/CPIO
    if [[ -n "${ROOTFS_CPIO_OFFSET:-}" ]]; then
        echo "| Initramfs | ✅ | CPIO at offset \`$ROOTFS_CPIO_OFFSET\` |"
    else
        echo "| Initramfs | ❓ | CPIO not identified |"
    fi

    # Check for SquashFS
    if [[ -n "${SQUASHFS_OFFSET:-}" ]]; then
        echo "| SquashFS | ✅ | Filesystem at offset \`$SQUASHFS_OFFSET\` |"
    else
        echo "| SquashFS | ❓ | SquashFS not identified |"
    fi
    echo ""

    echo "## Component Versions"
    echo ""
    echo "| Component | Version | Source |"
    echo "|-----------|---------|--------|"
    echo "| U-Boot | $UBOOT_VERSION | Binary strings |"
    echo "| Linux Kernel | $KERNEL_VERSION | Module vermagic |"

    # Get Buildroot version if available
    if [[ -n "$ROOTFS" && -f "$ROOTFS/etc/os-release" ]]; then
        br_version=$(grep "^VERSION=" "$ROOTFS/etc/os-release" 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "unknown")
        echo "| Buildroot | $br_version | /etc/os-release |"
    fi
    echo ""

    echo "## Partition Layout"
    echo ""
    echo "Derived from firmware offsets in \`binwalk-offsets.sh\`:"
    echo ""
    echo "| Region | Offset | Size | Type | Content |"
    echo "|--------|--------|------|------|---------|"

    # Calculate sizes from offsets
    if [[ -n "${BOOTLOADER_FIT_OFFSET_DEC:-}" ]]; then
        bl_size=$(( (KERNEL_FIT_OFFSET_DEC - BOOTLOADER_FIT_OFFSET_DEC) / 1024 / 1024 ))
        printf "| Bootloader | \`%s\` | ~%d MB | FIT | U-Boot + OP-TEE |\n" "$BOOTLOADER_FIT_OFFSET" "$bl_size"
    fi

    if [[ -n "${KERNEL_FIT_OFFSET_DEC:-}" ]]; then
        kernel_size=$(( (ROOTFS_CPIO_OFFSET_DEC - KERNEL_FIT_OFFSET_DEC) / 1024 / 1024 ))
        printf "| Kernel | \`%s\` | ~%d MB | FIT | Linux kernel + DTB |\n" "$KERNEL_FIT_OFFSET" "$kernel_size"
    fi

    if [[ -n "${ROOTFS_CPIO_OFFSET_DEC:-}" ]]; then
        cpio_size=$(( (SQUASHFS_OFFSET_DEC - ROOTFS_CPIO_OFFSET_DEC) / 1024 / 1024 ))
        printf "| Initramfs | \`%s\` | ~%d MB | CPIO | Early userspace |\n" "$ROOTFS_CPIO_OFFSET" "$cpio_size"
    fi

    if [[ -n "${SQUASHFS_OFFSET_DEC:-}" && -n "${SQUASHFS_SIZE:-}" ]]; then
        sq_size=$(( SQUASHFS_SIZE / 1024 / 1024 ))
        printf "| Root FS | \`%s\` | ~%d MB | SquashFS | Main filesystem |\n" "$SQUASHFS_OFFSET" "$sq_size"
    fi

    echo ""
    echo "*Note: Sizes calculated from offset differences. Actual partition table may differ.*"
    echo ""

    echo "## FIT Image Structure"
    echo ""

    echo "### Bootloader FIT (offset $BOOTLOADER_FIT_OFFSET)"
    echo ""
    if [[ -n "$BOOTLOADER_FIT_INFO" ]]; then
        echo '```'
        echo "$BOOTLOADER_FIT_INFO" | grep -A 50 "configurations" | head -30 || echo "Could not parse"
        echo '```'
    else
        echo "*FIT DTS not available*"
    fi
    echo ""

    echo "### Kernel FIT (offset $KERNEL_FIT_OFFSET)"
    echo ""
    if [[ -n "$KERNEL_FIT_INFO" ]]; then
        echo '```'
        echo "$KERNEL_FIT_INFO" | grep -A 50 "configurations" | head -30 || echo "Could not parse"
        echo '```'
    else
        echo "*FIT DTS not available*"
    fi
    echo ""

    echo "## A/B Partition Scheme"
    echo ""

    # Count FIT images to determine if A/B redundancy is present
    bootloader_fits=$(find "$EXTRACT_DIR" -name "system.dtb" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$bootloader_fits" -gt 2 ]]; then
        echo "**Evidence of A/B redundancy:**"
        echo ""
        echo "- Found $bootloader_fits FIT image DTBs in extraction"
        echo "- Multiple bootloader/kernel slots suggests A/B OTA support"
    else
        echo "*No clear evidence of A/B partition scheme found.*"
    fi
    echo ""

    echo "## Boot Configuration"
    echo ""

    # Extract boot arguments from the largest DTS (already found above)
    if [[ -n "$KERNEL_FULL_DTS" && -f "$KERNEL_FULL_DTS" ]]; then
        bootargs=$(grep -oP 'bootargs = "\K[^"]+' "$KERNEL_FULL_DTS" 2>/dev/null || true)
        if [[ -n "$bootargs" ]]; then
            echo "### Kernel Command Line"
            echo ""
            echo '```'
            echo "$bootargs"
            echo '```'
            echo ""
        fi

        # Extract UART/console settings
        baudrate=$(grep -oP 'rockchip,baudrate = <\K[^>]+' "$KERNEL_FULL_DTS" 2>/dev/null || true)
        # Try to extract console from bootargs or stdout-path
        console=$(grep -oP 'stdout-path = "\K[^"]+' "$KERNEL_FULL_DTS" 2>/dev/null | head -1 || true)
        [[ -z "$console" ]] && console=$(echo "$bootargs" | grep -oE 'console=[^ ]+' | cut -d= -f2 || true)

        if [[ -n "$baudrate" || -n "$console" ]]; then
            echo "### Console Configuration"
            echo ""
            echo "| Parameter | Value | Source |"
            echo "|-----------|-------|--------|"
            if [[ -n "$baudrate" ]]; then
                baud_dec=$(printf "%d" "$baudrate" 2>/dev/null || echo "$baudrate")
                echo "| Baud Rate | $baud_dec | DTS rockchip,baudrate |"
            fi
            if [[ -n "$console" ]]; then
                echo "| Console | $console | DTS stdout-path/bootargs |"
            fi
            echo ""
        fi
    fi

} > "$OUTPUT_DIR/boot-process.md"

success "Wrote boot-process.md"
