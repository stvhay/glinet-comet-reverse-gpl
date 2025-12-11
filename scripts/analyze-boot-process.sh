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
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing boot process in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")

section "Analyzing boot chain"

# Extract component information
# FIT image offsets (from binwalk analysis)
BOOTLOADER_FIT_OFFSET="0x8F1B4"
KERNEL_FIT_OFFSET="0x49B1B4"

# Get DTS files if available
BOOTLOADER_DTS="$EXTRACT_DIR/8F1B4/system.dtb"
KERNEL_DTS="$EXTRACT_DIR/49B1B4/system.dtb"

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
    echo "| Property | Value |"
    echo "|----------|-------|"
    echo "| **SoC** | Rockchip RV1126 |"
    echo "| **Architecture** | ARM Cortex-A7 (32-bit ARMv7) |"
    echo "| **Storage** | eMMC |"

    # Try to extract compatible string from DTS
    if [[ -n "$KERNEL_FIT_INFO" ]]; then
        # Look for kernel DTS in larger offset
        KERNEL_FULL_DTS="$EXTRACT_DIR/1C597B4/system.dtb"
        if [[ -f "$KERNEL_FULL_DTS" ]]; then
            compat=$(grep -oP 'compatible = "\K[^"]+' "$KERNEL_FULL_DTS" 2>/dev/null | head -1 || true)
            if [[ -n "$compat" ]]; then
                echo "| **Device Tree Compatible** | \`$compat\` |"
            fi
        fi
    fi
    echo ""

    echo "## Boot Chain"
    echo ""
    echo '```'
    cat << 'BOOTCHAIN'
┌─────────────┐
│  Power On   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  BootROM    │  Rockchip mask ROM (fixed in silicon)
│  (BROM)     │  - Initializes basic hardware
└──────┬──────┘  - Loads SPL from eMMC/SD
       │
       ▼
┌─────────────┐
│  SPL/TPL    │  Secondary Program Loader
│             │  - DDR memory initialization
└──────┬──────┘  - Loads U-Boot FIT image
       │
       ▼
┌─────────────┐
│  OP-TEE     │  Trusted Execution Environment
│  (tee.bin)  │  - Secure world initialization
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  U-Boot     │  - Hardware initialization
│             │  - Loads kernel FIT image
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Linux      │  - Main operating system
│  Kernel     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Initramfs  │  - Early userspace init
│             │  - Mounts SquashFS root
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  SquashFS   │  Main root filesystem
│  Rootfs     │  - Read-only
└─────────────┘
BOOTCHAIN
    echo '```'
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
    echo "Based on firmware structure analysis:"
    echo ""
    echo "| Partition | Name | Size | Filesystem | Purpose |"
    echo "|-----------|------|------|------------|---------|"
    echo "| 1 | uboot | ~2 MB | FIT Image | U-Boot + OP-TEE |"
    echo "| 2 | reserved | ~2 MB | Raw | Rockchip reserved |"
    echo "| 3 | dtb1 | ~12 MB | FIT Image | Kernel slot A |"
    echo "| 4 | dtb2 | ~12 MB | FIT Image | Kernel slot B |"
    echo "| 5 | misc | ~1 MB | Raw | Boot control |"
    echo "| 6 | rootfs | ~232 MB | SquashFS | Root filesystem |"
    echo "| 7 | oem | ~6 MB | EXT4 | OEM data |"
    echo "| 8 | userdata | ~5 MB | EXT4 | User data |"
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
    echo "The device uses A/B redundancy for safe OTA updates:"
    echo ""
    echo "| Slot | Kernel Partition | Purpose |"
    echo "|------|------------------|---------|"
    echo "| A | dtb1 (p3) | Recovery / Fallback |"
    echo "| B | dtb2 (p4) | Normal boot |"
    echo ""
    echo "Boot selection is controlled by the misc partition."
    echo ""

    echo "## Boot Configuration"
    echo ""

    # Extract boot arguments from DTS
    KERNEL_FULL_DTS="$EXTRACT_DIR/1C597B4/system.dtb"
    if [[ -f "$KERNEL_FULL_DTS" ]]; then
        bootargs=$(grep -oP 'bootargs = "\K[^"]+' "$KERNEL_FULL_DTS" 2>/dev/null || true)
        if [[ -n "$bootargs" ]]; then
            echo "### Kernel Command Line"
            echo ""
            echo '```'
            echo "$bootargs"
            echo '```'
            echo ""
        fi

        # Extract UART settings
        baudrate=$(grep -oP 'rockchip,baudrate = <\K[^>]+' "$KERNEL_FULL_DTS" 2>/dev/null || true)
        if [[ -n "$baudrate" ]]; then
            baud_dec=$(printf "%d" "$baudrate" 2>/dev/null || echo "$baudrate")
            echo "### Console Configuration"
            echo ""
            echo "| Parameter | Value |"
            echo "|-----------|-------|"
            echo "| Baud Rate | $baud_dec |"
            echo "| Console | ttyFIQ0 |"
            echo ""
        fi
    fi

    echo "## Methodology"
    echo ""
    echo "This analysis was performed by:"
    echo "1. Running binwalk to identify firmware structure"
    echo "2. Extracting FIT image DTS from known offsets"
    echo "3. Parsing device tree for boot configuration"
    echo "4. Extracting version strings from binaries"

} > "$OUTPUT_DIR/boot-process.md"

success "Wrote boot-process.md"
