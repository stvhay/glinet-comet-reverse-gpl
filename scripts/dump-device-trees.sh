#!/usr/bin/env bash
# Extract and decompile Device Tree Blobs (DTB) to Device Tree Source (DTS)
#
# Usage: ./scripts/dump-device-trees.sh [firmware.img]
#
# Outputs:
#   output/dtb/uboot-fit.dtb      - U-Boot FIT image structure (describes boot components)
#   output/dtb/uboot-fit.dts      - Decompiled U-Boot FIT structure
#   output/dtb/kernel-fit.dtb     - Kernel FIT image (contains kernel + hardware DTB)
#   output/dtb/kernel-fit.dts     - Decompiled kernel FIT (includes hardware device tree)
#
# The kernel FIT image in this firmware contains the actual hardware device tree
# embedded within it, so kernel-fit.dts contains the RV1126 board configuration.
#
# FIT images use the same FDT format as device trees, so both are extracted
# using the same DTB/DTS tooling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command dtc
require_command dd

# DTB output directory
DTB_DIR="$OUTPUT_DIR/dtb"
mkdir -p "$DTB_DIR"

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Extracting device trees from: $FIRMWARE"

# Load offsets from binwalk analysis
load_firmware_offsets

# ==============================================================================
# Helper: Extract and decompile a DTB/FIT image
# ==============================================================================
extract_and_decompile() {
    local name="$1"
    local offset="$2"
    local description="$3"

    local dtb_file="$DTB_DIR/${name}.dtb"
    local dts_file="$DTB_DIR/${name}.dts"

    # Get size from FDT header
    local size
    size=$(get_fdt_size "$FIRMWARE" "$offset")

    # Sanity check size (max 50MB)
    if [[ "$size" -le 0 || "$size" -gt 52428800 ]]; then
        warn "Invalid FDT size at offset $offset: $size bytes"
        return 1
    fi

    info "Extracting $name from offset $offset (size: $size bytes)"
    info "  $description"

    # Extract DTB
    if ! extract_fdt "$FIRMWARE" "$offset" "$size" "$dtb_file"; then
        error "Failed to extract $name"
        return 1
    fi
    success "Wrote $dtb_file"

    # Decompile to DTS
    info "Decompiling $name to DTS..."
    if decompile_dtb "$dtb_file" "$dts_file"; then
        success "Wrote $dts_file"
    else
        warn "Could not decompile $name - may require manual analysis"
    fi
}

# ==============================================================================
# Extract Bootloader FIT Image
# Contains: U-Boot, OP-TEE, and U-Boot device tree
# Offset source: BOOTLOADER_FIT_OFFSET from binwalk-offsets.sh
# ==============================================================================
section "Bootloader FIT Image (U-Boot)"

if [[ -n "${BOOTLOADER_FIT_OFFSET_DEC:-}" ]]; then
    extract_and_decompile "uboot-fit" "$BOOTLOADER_FIT_OFFSET_DEC" \
        "FIT container with U-Boot, OP-TEE, and U-Boot DTB"
else
    warn "BOOTLOADER_FIT_OFFSET not available - run analyze-binwalk.sh first"
fi

# ==============================================================================
# Extract Kernel FIT Image
# Contains: Linux kernel and hardware device tree
# Offset source: KERNEL_FIT_OFFSET from binwalk-offsets.sh
# Note: This FIT image contains the actual hardware DTB for the RV1126 board
# ==============================================================================
section "Kernel FIT Image"

if [[ -n "${KERNEL_FIT_OFFSET_DEC:-}" ]]; then
    extract_and_decompile "kernel-fit" "$KERNEL_FIT_OFFSET_DEC" \
        "FIT container with Linux kernel and RV1126 hardware DTB"
else
    warn "KERNEL_FIT_OFFSET not available - run analyze-binwalk.sh first"
fi

# ==============================================================================
# Summary
# ==============================================================================
section "Summary"

echo ""
echo "Extracted device trees:"
for f in "$DTB_DIR"/*.dtb "$DTB_DIR"/*.dts; do
    [[ -f "$f" ]] || continue
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
    printf "  %-20s %8d bytes\n" "$(basename "$f")" "$size"
done

echo ""
echo "File descriptions:"
echo "  uboot-fit.dts   - U-Boot FIT structure (boot component manifest)"
echo "  kernel-fit.dts  - Kernel FIT with embedded RV1126 hardware device tree"

success "Device tree extraction complete: $DTB_DIR"
