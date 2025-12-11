#!/usr/bin/env bash
# Extract Linux kernel images from firmware FIT images
#
# Usage: ./scripts/dump-kernels.sh [firmware.img]
#
# Outputs:
#   output/kernel/boot-kernel.bin - Main boot kernel
#
# The GL.iNet Comet firmware uses Rockchip FIT (Flattened Image Tree) format.
# The FIT wrapper is a small DTB containing metadata (data-position, data-size)
# for each component: kernel, fdt (device tree), and resource (boot logos).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command dd
require_command dtc

# Kernel output directory
KERNEL_DIR="$OUTPUT_DIR/kernel"
mkdir -p "$KERNEL_DIR"

# Get firmware
FIRMWARE=$(get_firmware "${1:-}")
info "Extracting kernels from: $FIRMWARE"

# ==============================================================================
# Find FIT wrapper by scanning for small DTB with FIT structure
# ==============================================================================
# FIT wrappers are small DTBs (1-4KB) containing metadata about larger payloads.
# They have FDT magic (0xd00dfeed) and contain "images" and "kernel" nodes.
# ==============================================================================

find_fit_wrapper() {
    local search_start="$1"
    local description="$2"

    info "Scanning for FIT wrapper starting at offset $search_start" >&2

    # Get all DTB offsets from binwalk analysis
    local binwalk_output
    binwalk_output=$(binwalk "$FIRMWARE" 2>/dev/null | grep -i "device tree blob" || true)

    # Find small DTBs (< 4KB) after the search start offset
    while read -r line; do
        [[ -z "$line" ]] && continue

        local offset size
        offset=$(echo "$line" | awk '{print $1}')
        [[ -z "$offset" || ! "$offset" =~ ^[0-9]+$ ]] && continue
        [[ "$offset" -lt "$search_start" ]] && continue

        # Extract size from "total size: NNNN bytes"
        size=$(echo "$line" | grep -oE "total size: [0-9]+" | grep -oE "[0-9]+")
        [[ -z "$size" ]] && continue

        # FIT wrappers are small (< 4KB)
        if [[ "$size" -lt 4096 ]]; then
            # Verify it's a FIT by checking for "images" node
            local tmp_dtb="/tmp/fit-check-$$.dtb"
            local tmp_dts="/tmp/fit-check-$$.dts"

            dd if="$FIRMWARE" of="$tmp_dtb" bs=1 skip="$offset" count="$size" 2>/dev/null
            if dtc -I dtb -O dts -o "$tmp_dts" "$tmp_dtb" 2>/dev/null; then
                if grep -q "images {" "$tmp_dts" && grep -q "kernel {" "$tmp_dts"; then
                    rm -f "$tmp_dtb" "$tmp_dts"
                    echo "$offset"
                    return 0
                fi
            fi
            rm -f "$tmp_dtb" "$tmp_dts"
        fi
    done <<< "$binwalk_output"

    return 1
}

# ==============================================================================
# Extract kernel from FIT image
# ==============================================================================
extract_kernel_from_fit() {
    local name="$1"
    local fit_offset="$2"
    local description="$3"

    local output_file="$KERNEL_DIR/${name}.bin"
    local fit_wrapper="/tmp/${name}-fit-wrapper.dtb"
    local fit_dts="/tmp/${name}-fit-wrapper.dts"

    info "Processing $name"
    info "  FIT wrapper at offset: $fit_offset"
    info "  $description"

    # Get FIT wrapper size from DTB header
    local fit_size
    fit_size=$(get_fdt_size "$FIRMWARE" "$fit_offset")

    if [[ "$fit_size" -le 0 || "$fit_size" -gt 8192 ]]; then
        warn "FIT wrapper size invalid: $fit_size bytes"
        return 1
    fi

    info "  FIT wrapper size: $fit_size bytes"

    # Extract FIT wrapper DTB
    dd if="$FIRMWARE" of="$fit_wrapper" bs=1 skip="$fit_offset" count="$fit_size" 2>/dev/null

    # Decompile to get structure
    if ! dtc -I dtb -O dts -o "$fit_dts" "$fit_wrapper" 2>/dev/null; then
        warn "Could not decompile FIT wrapper for $name"
        rm -f "$fit_wrapper"
        return 1
    fi

    # Parse kernel data-position and data-size from DTS
    # These values are relative to the FIT image start
    local kernel_offset kernel_size
    kernel_offset=$(grep -A10 'kernel {' "$fit_dts" | grep 'data-position' | grep -oE '<0x[0-9a-fA-F]+>' | tr -d '<>' | head -1)
    kernel_size=$(grep -A10 'kernel {' "$fit_dts" | grep 'data-size' | grep -oE '<0x[0-9a-fA-F]+>' | tr -d '<>' | head -1)

    if [[ -z "$kernel_offset" || -z "$kernel_size" ]]; then
        warn "Could not find kernel offset/size in FIT image for $name"
        cat "$fit_dts"
        rm -f "$fit_wrapper" "$fit_dts"
        return 1
    fi

    # Convert to decimal
    kernel_offset=$((kernel_offset))
    kernel_size=$((kernel_size))

    # Calculate absolute offset in firmware
    local absolute_offset=$((fit_offset + kernel_offset))

    info "  Kernel data-position: 0x$(printf '%X' $kernel_offset) (relative)"
    info "  Kernel absolute offset: $absolute_offset"
    info "  Kernel size: $kernel_size bytes ($(numfmt --to=iec $kernel_size))"

    # Extract kernel
    dd if="$FIRMWARE" of="$output_file" bs=1 skip="$absolute_offset" count="$kernel_size" 2>/dev/null

    # Verify extraction
    if [[ ! -s "$output_file" ]]; then
        error "Failed to extract kernel for $name"
        rm -f "$fit_wrapper" "$fit_dts"
        return 1
    fi

    success "Extracted $output_file"

    # Identify kernel type
    local file_type
    file_type=$(file "$output_file")
    info "  Type: $file_type"

    # Try to get version string
    local version
    version=$(strings "$output_file" 2>/dev/null | grep "Linux version" | head -1 || true)
    if [[ -n "$version" ]]; then
        info "  Version: $version"
    fi

    # Cleanup
    rm -f "$fit_wrapper" "$fit_dts"
}

# ==============================================================================
# Main extraction
# ==============================================================================

section "Boot Kernel"

# Find boot kernel FIT wrapper (first FIT after 4MB, where kernel partition starts)
BOOT_FIT_OFFSET=$(find_fit_wrapper 4000000 "Boot kernel FIT")

if [[ -n "$BOOT_FIT_OFFSET" ]]; then
    extract_kernel_from_fit "boot-kernel" "$BOOT_FIT_OFFSET" \
        "Main boot kernel from kernel partition"
else
    warn "Could not find boot kernel FIT wrapper"
fi

section "Recovery Kernel"

# Find recovery kernel FIT wrapper (FIT after 12MB, where recovery partition typically starts)
RECOVERY_FIT_OFFSET=$(find_fit_wrapper 12000000 "Recovery kernel FIT")

if [[ -n "$RECOVERY_FIT_OFFSET" ]]; then
    extract_kernel_from_fit "recovery-kernel" "$RECOVERY_FIT_OFFSET" \
        "Recovery kernel from recovery partition"
else
    info "No recovery kernel FIT found (may not be present in this firmware)"
fi

# ==============================================================================
# Summary
# ==============================================================================
section "Summary"

echo ""
echo "Extracted kernels:"
for f in "$KERNEL_DIR"/*.bin; do
    [[ -f "$f" ]] || continue
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
    printf "  %-25s %s\n" "$(basename "$f")" "$(numfmt --to=iec "$size")"
done

success "Kernel extraction complete: $KERNEL_DIR"
