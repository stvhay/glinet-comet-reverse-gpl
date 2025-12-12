#!/usr/bin/env bash
# Test JSON helper functions in lib/common.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

section "Testing JSON Helpers"

# Test 1: Basic JSON output
echo ""
info "Test 1: Basic JSON object with source metadata"
json_start
json_field "test_string" "Hello, World!" "test" "echo 'Hello, World!'"
json_field "test_number_str" "42" "test" "echo 42"
json_end

# Test 2: JSON with numeric fields
echo ""
echo ""
info "Test 2: Numeric fields (no quotes around values)"
json_start
json_field_number "count" "123"
json_field_number "size" "1048576" "stat" "stat -f%z file.bin"
json_end

# Test 3: JSON with special characters that need escaping
echo ""
echo ""
info "Test 3: String escaping (quotes, backslashes, newlines)"
json_start
json_field "quoted" 'He said "hello"'
json_field "backslash" 'C:\Windows\System32'
json_field "newline" $'Line 1\nLine 2'
json_field "tab" $'Column1\tColumn2'
json_end

# Test 4: JSON arrays
echo ""
echo ""
info "Test 4: JSON arrays"
json_start
json_field "name" "Test Firmware"
json_array_start "files"
json_array_item "kernel.bin"
json_array_item "rootfs.squashfs"
json_array_item "uboot.bin"
json_array_end
json_end

# Test 5: Complex example matching analyze_test.sh pattern
echo ""
echo ""
info "Test 5: Complex example with multiple field types"
json_start
json_field "firmware_version" "1.7.2" "filename" "basename firmware.img | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+'"
json_field_number "firmware_size" "12582912" "stat" "stat -f%z firmware.img"
json_field "kernel_offset" "0x2000" "binwalk" "binwalk firmware.img | grep 'Linux kernel'"
json_array_start "reference_sources"
json_array_item "https://gitlab.com/firefly-linux/kernel"
json_array_item "https://github.com/rockchip-linux/kernel"
json_array_end
json_field "gpl_implications" "Device tree uses GPL-2.0+ licensed Rockchip sources" "analysis" "diff reference.dts extracted.dts"
json_end

success "All JSON helper tests completed"
