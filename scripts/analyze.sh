#!/usr/bin/env bash
# GL.iNet Comet Firmware Analysis - Main Script
#
# Usage: ./scripts/analyze.sh [OPTIONS] [FIRMWARE_URL_OR_PATH]
#
# This script orchestrates all analysis modules to generate a comprehensive
# GPL compliance report for the GL.iNet Comet (GL-RM1) firmware.
#
# Modules (can also be run individually):
#   analyze-binwalk.sh         - Firmware structure analysis
#   analyze-device-trees.sh    - Device tree extraction
#   analyze-uboot.sh           - U-Boot bootloader analysis
#   analyze-boot-process.sh    - Boot chain documentation
#   analyze-rootfs.sh          - Rootfs, licenses, packages
#   analyze-network-services.sh - Network attack surface
#   analyze-proprietary-blobs.sh - Vendor binary inventory
#   analyze-secure-boot.sh     - Secure boot configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# ==============================================================================
# Command-line parsing
# ==============================================================================
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [FIRMWARE_URL_OR_PATH]

Analyze GL.iNet Comet (GL-RM1) firmware for GPL compliance.

Options:
  -h, --help     Show this help message
  -l, --list     List known firmware versions
  -o DIR         Output directory (default: output/)
  -m MODULE      Run only specific module(s), comma-separated
                 Available: binwalk,device-trees,uboot,boot-process,
                           rootfs,network-services,proprietary-blobs,secure-boot,all
  -v, --verbose  Verbose output

Arguments:
  FIRMWARE_URL_OR_PATH   URL or local path to firmware .img file

Examples:
  $0                              # Analyze default firmware (1.7.2)
  $0 -m rootfs,licenses           # Only run rootfs analysis
  $0 https://example.com/fw.img   # Analyze specific firmware
  $0 ./local-firmware.img         # Analyze local file

Environment Variables:
  FIRMWARE_URL   Override firmware URL
  OUTPUT_DIR     Override output directory
  WORK_DIR       Override working directory

EOF
}

list_versions() {
    echo "Known Firmware Versions:"
    echo "  1.7.2 - https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
    echo ""
    echo "Check https://dl.gl-inet.com/kvm/rm1/ for other versions."
}

# Parse arguments
MODULES="all"
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -l|--list)
            list_versions
            exit 0
            ;;
        -o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -m)
            MODULES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="1"
            shift
            ;;
        -*)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            FIRMWARE_ARG="$1"
            shift
            ;;
    esac
done

# ==============================================================================
# Main
# ==============================================================================

# Initialize
init_dirs

# Banner
echo "=============================================="
echo "  GL.iNet Comet (RM1) Firmware Analysis"
echo "=============================================="
echo ""

# Get firmware
FIRMWARE=$(get_firmware "${FIRMWARE_ARG:-}")
FIRMWARE_FILE=$(basename "$FIRMWARE")
FIRMWARE_VERSION=$(extract_version "$FIRMWARE")

info "Firmware: $FIRMWARE_FILE"
info "Version: $FIRMWARE_VERSION"
info "Output: $OUTPUT_DIR"
echo ""

# Run extraction (shared by all modules)
section "Extracting Firmware"
EXTRACT_DIR=$(extract_firmware "$FIRMWARE")
export EXTRACT_DIR
export FIRMWARE
export OUTPUT_DIR
export WORK_DIR

# Determine which modules to run
run_module() {
    local name="$1"
    local script="$SCRIPT_DIR/analyze-$name.sh"

    if [[ ! -x "$script" ]]; then
        warn "Module not found: $script"
        return 1
    fi

    section "Running: $name"
    if [[ -n "$VERBOSE" ]]; then
        "$script" "$FIRMWARE"
    else
        "$script" "$FIRMWARE" 2>&1 | grep -E "^\[|Wrote" || true
    fi
}

should_run() {
    local name="$1"
    [[ "$MODULES" == "all" ]] || [[ ",$MODULES," == *",$name,"* ]]
}

# Run selected modules
should_run "binwalk" && run_module "binwalk"
should_run "device-trees" && run_module "device-trees"
should_run "uboot" && run_module "uboot"
should_run "boot-process" && run_module "boot-process"
should_run "rootfs" && run_module "rootfs"
should_run "network-services" && run_module "network-services"
should_run "proprietary-blobs" && run_module "proprietary-blobs"
should_run "secure-boot" && run_module "secure-boot"

# ==============================================================================
# Generate Summary
# ==============================================================================
section "Generating Summary"

ROOTFS=$(find_rootfs "$EXTRACT_DIR" 2>/dev/null || true)

{
    cat << EOF
# GPL Compliance Analysis Summary

**GL.iNet Comet (RM1) Firmware**

Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Firmware Source

| Property | Value |
|----------|-------|
| Version | $FIRMWARE_VERSION |
| Filename | \`$FIRMWARE_FILE\` |

## Analysis Modules

Each module can be run individually for specific analysis:

| Module | Output |
|--------|--------|
EOF

    # Generate module table dynamically from script headers
    for script in "$SCRIPT_DIR"/analyze-*.sh; do
        [[ -f "$script" ]] || continue
        name=$(basename "$script")
        # Extract output file from "# Outputs:" line in header
        output=$(grep -m1 "^# Outputs:" "$script" 2>/dev/null | sed 's/^# Outputs: *//' || echo "-")
        [[ -z "$output" ]] && output="-"
        # Clean up output path to just filename
        output=$(basename "$output" 2>/dev/null || echo "$output")
        echo "| \`$name\` | $output |"
    done

    cat << 'EOF'

## Output Files

| File | Description |
|------|-------------|
EOF

    # List all generated files
    for f in "$OUTPUT_DIR"/*.md; do
        [[ -f "$f" ]] || continue
        name=$(basename "$f")
        # Get first line after header for description
        desc=$(sed -n '3p' "$f" 2>/dev/null | head -c 50 || echo "Analysis output")
        echo "| [$name]($name) | $desc |"
    done

    cat << EOF

## GPL Components Identified

EOF

    if [[ -n "$ROOTFS" && -f "$ROOTFS/etc/os-release" ]]; then
        echo "### Build System"
        echo ""
        grep -E "^(NAME|VERSION|PRETTY_NAME)=" "$ROOTFS/etc/os-release" 2>/dev/null | \
            while read -r line; do echo "- $line"; done || true
        echo ""
    fi

    if [[ -f "$ROOTFS/bin/busybox" ]]; then
        version=$(strings "$ROOTFS/bin/busybox" 2>/dev/null | grep -i "busybox v" | head -1 || echo "unknown")
        echo "### BusyBox"
        echo ""
        echo "- **Version:** \`$version\`"
        echo ""
    fi

} > "$OUTPUT_DIR/SUMMARY.md"

success "Wrote SUMMARY.md"

# ==============================================================================
# Complete
# ==============================================================================
section "Analysis Complete"

echo ""
echo "Output files:"
find "$OUTPUT_DIR" -maxdepth 1 -name "*.md" -type f -printf "  %-40f %s\n" 2>/dev/null | sort
echo ""
echo "Run individual modules with:"
echo "  ./scripts/analyze-<module>.sh $FIRMWARE"
