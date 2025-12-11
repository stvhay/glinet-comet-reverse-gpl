#!/usr/bin/env bash
# Extract and analyze Device Tree Blobs from firmware
#
# Usage: ./scripts/analyze-device-trees.sh [firmware.img]
#
# Outputs: output/device-trees.md
#
# This script extracts DTB files from the firmware and analyzes:
# - Device tree model and compatible strings
# - FIT image structure (if present)
# - Hardware configuration details

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk

# Get firmware and extract
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing device trees in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")

# Find DTB files
section "Finding Device Tree Blobs"
DTB_FILES=$(find_fit_images "$EXTRACT_DIR")
DTB_COUNT=$(echo "$DTB_FILES" | grep -c "." || echo "0")

info "Found $DTB_COUNT DTB/DTS files"

# Generate output
{
    generate_header "Device Tree Analysis" \
        "Device Trees found in the firmware image."

    if [[ -n "$DTB_FILES" && "$DTB_COUNT" -gt 0 ]]; then
        DTB_NUM=0
        while IFS= read -r dtb_file; do
            [[ -z "$dtb_file" ]] && continue
            DTB_NUM=$((DTB_NUM + 1))

            # Get relative path for display
            rel_path="${dtb_file#$EXTRACT_DIR/}"
            offset_dir=$(dirname "$rel_path" | head -1)

            echo "## DTB #$DTB_NUM: \`$(basename "$dtb_file")\` (offset $offset_dir)"
            echo ""

            # Get file size
            dtb_size=$(stat -f%z "$dtb_file" 2>/dev/null || stat -c%s "$dtb_file" 2>/dev/null || echo "unknown")
            echo "- **Size:** $dtb_size bytes"

            # Read content (binwalk extracts DTS as text, not binary DTB)
            DTS_CONTENT=$(cat "$dtb_file" 2>/dev/null | head -200 || true)

            # Determine type
            if echo "$DTS_CONTENT" | grep -q "FIT Image\|fit.*source"; then
                echo "- **Type:** FIT Image (Flattened Image Tree)"
            elif echo "$DTS_CONTENT" | grep -q "U-Boot"; then
                echo "- **Type:** U-Boot Device Tree"
            else
                echo "- **Type:** Device Tree"
            fi

            # Extract model and compatible strings
            MODEL=$(echo "$DTS_CONTENT" | grep -E "^\s*model\s*=" | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/' || true)
            COMPAT=$(echo "$DTS_CONTENT" | grep -E "^\s*compatible\s*=" | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/' || true)

            if [[ -n "$MODEL" ]]; then
                echo "- **Model:** $MODEL"
            fi
            if [[ -n "$COMPAT" ]]; then
                echo "- **Compatible:** \`$COMPAT\`"
            fi

            # Check if this is a FIT image (contains images/configurations nodes)
            if echo "$DTS_CONTENT" | grep -q "description.*FIT"; then
                echo ""
                echo "### FIT Image Contents"
                echo ""
                echo '```'
                echo "$DTS_CONTENT" | grep -E "^\s*(description|type|arch|os|compression|algo|key-name-hint|sign-images)\s*=" | head -30 || true
                echo '```'
            fi

            # Extract UART/serial settings if present
            if echo "$DTS_CONTENT" | grep -q "baudrate\|fiq-debugger"; then
                echo ""
                echo "### Serial/UART Configuration"
                echo ""
                echo '```'
                echo "$DTS_CONTENT" | grep -A 10 "fiq-debugger\|serial@" | head -20 || true
                echo '```'
            fi

            echo ""
        done <<< "$DTB_FILES"

        echo "---"
        echo ""
        echo "**Total Device Trees found:** $DTB_COUNT"
    else
        echo "*No Device Trees found in extracted firmware*"
    fi

} > "$OUTPUT_DIR/device-trees.md"

success "Wrote device-trees.md"
