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
    echo "$BINWALK_OUTPUT"
    echo '```'
    echo ""

    echo "## Identified Components"
    echo ""
    echo "| Offset | Type | Description |"
    echo "|--------|------|-------------|"

    # Parse binwalk output into table
    echo "$BINWALK_OUTPUT" | tail -n +4 | while read -r line; do
        if [[ -n "$line" ]]; then
            offset=$(echo "$line" | awk '{print $1}')
            hex_offset=$(printf "0x%X" "$offset" 2>/dev/null || echo "$offset")
            # Get everything after the offset
            desc=$(echo "$line" | cut -d' ' -f2-)
            type=$(echo "$desc" | awk '{print $1}')
            echo "| $hex_offset | $type | $desc |"
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
