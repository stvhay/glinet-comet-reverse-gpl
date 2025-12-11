#!/usr/bin/env bash
# Common functions and variables for analysis scripts
#
# Usage: source "$(dirname "$0")/lib/common.sh"
#
# Provides:
#   - Color output functions (info, warn, error, success)
#   - SCRIPT_DIR, PROJECT_ROOT, OUTPUT_DIR, WORK_DIR variables
#   - require_command() - Check for required commands
#   - download_firmware() - Download firmware if needed
#   - extract_firmware() - Run binwalk extraction
#   - find_rootfs() - Locate SquashFS rootfs in extractions

set -euo pipefail

# Determine paths
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(dirname "$SCRIPT_DIR")}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"
WORK_DIR="${WORK_DIR:-/tmp/fw_analysis}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$PROJECT_ROOT/downloads}"

# Default firmware URL
DEFAULT_FIRMWARE_URL="https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output functions
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
section() { echo -e "\n${BLUE}=== $* ===${NC}"; }

# Check for required command
require_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        error "Required command not found: $cmd"
        error "Please run this script within 'nix develop' shell"
        exit 1
    fi
}

# Initialize directories
init_dirs() {
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$WORK_DIR"
    mkdir -p "$DOWNLOAD_DIR"
}

# Get firmware path, downloading if necessary
# Usage: FIRMWARE=$(get_firmware "$URL_OR_PATH")
get_firmware() {
    local source="${1:-$DEFAULT_FIRMWARE_URL}"

    if [[ -f "$source" ]]; then
        # Local file
        echo "$source"
        return 0
    fi

    # URL - download to work dir
    local filename
    filename=$(basename "$source")
    local dest="$WORK_DIR/$filename"

    if [[ ! -f "$dest" ]]; then
        info "Downloading firmware: $source"
        curl -L -o "$dest" "$source"
    fi

    echo "$dest"
}

# Extract firmware version from filename
# Usage: VERSION=$(extract_version "$FIRMWARE_PATH")
extract_version() {
    local firmware="$1"
    local filename
    filename=$(basename "$firmware")

    # Try to extract version like "1.7.2" from filename
    if [[ "$filename" =~ RM1-([0-9]+\.[0-9]+\.[0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo "unknown"
    fi
}

# Run binwalk extraction if needed
# Usage: EXTRACT_DIR=$(extract_firmware "$FIRMWARE")
extract_firmware() {
    local firmware="$1"
    local extract_base="$WORK_DIR/extractions"
    local filename
    filename=$(basename "$firmware")
    local extract_dir="$extract_base/${filename}.extracted"

    mkdir -p "$extract_base"

    if [[ ! -d "$extract_dir" ]]; then
        info "Extracting firmware with binwalk..."
        (cd "$extract_base" && binwalk -e --run-as=root "$firmware" 2>/dev/null) || true
    fi

    echo "$extract_dir"
}

# Find SquashFS rootfs in extractions
# Usage: ROOTFS=$(find_rootfs "$EXTRACT_DIR")
find_rootfs() {
    local extract_dir="$1"
    local rootfs

    # Look for squashfs-root directory
    rootfs=$(find "$extract_dir" -type d -name "squashfs-root" 2>/dev/null | head -1)

    if [[ -z "$rootfs" || ! -d "$rootfs" ]]; then
        error "Could not find SquashFS rootfs in $extract_dir"
        return 1
    fi

    echo "$rootfs"
}

# Find FIT image DTS files in extractions
# Usage: FIT_FILES=$(find_fit_images "$EXTRACT_DIR")
find_fit_images() {
    local extract_dir="$1"
    find "$extract_dir" -name "system.dtb" -type f 2>/dev/null | sort
}

# Generate markdown header for output files
# Usage: generate_header "Title" "Description"
generate_header() {
    local title="$1"
    local description="${2:-}"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    echo "# $title"
    echo ""
    echo "**GL.iNet Comet (GL-RM1) Firmware**"
    echo ""
    echo "Generated: $timestamp"
    if [[ -n "$description" ]]; then
        echo ""
        echo "$description"
    fi
    echo ""
}

# Write content to output file with logging
# Usage: write_output "filename.md" "$content"
write_output() {
    local filename="$1"
    local content="$2"
    local filepath="$OUTPUT_DIR/$filename"

    echo "$content" > "$filepath"
    info "Wrote $filename"
}

# Load firmware offsets from binwalk analysis artifact
# Usage: load_firmware_offsets
# Sets: BOOTLOADER_FIT_OFFSET, KERNEL_FIT_OFFSET, SQUASHFS_OFFSET, etc.
load_firmware_offsets() {
    local offsets_file="$OUTPUT_DIR/binwalk-offsets.sh"

    if [[ ! -f "$offsets_file" ]]; then
        error "Firmware offsets not found: $offsets_file"
        error "Run analyze-binwalk.sh first to generate offset artifacts"
        return 1
    fi

    # shellcheck source=/dev/null
    source "$offsets_file"
    info "Loaded firmware offsets from binwalk analysis"
}

# Require firmware offsets to be available
# Usage: require_firmware_offsets
require_firmware_offsets() {
    if [[ -z "${BOOTLOADER_FIT_OFFSET:-}" ]]; then
        load_firmware_offsets
    fi
}

# ==============================================================================
# FDT (Flattened Device Tree) / DTB helper functions
# Reference: https://devicetree-specification.readthedocs.io/en/stable/flattened-format.html
# ==============================================================================

# FDT magic number: 0xd00dfeed (big-endian)
# This 4-byte value appears at offset 0 of every valid DTB/FIT image
# Reference: Device Tree Specification Section 5.2 "Header"
FDT_MAGIC="d00dfeed"

# FDT header field offsets (all big-endian 32-bit values)
# Reference: Device Tree Specification Section 5.2
FDT_HEADER_TOTALSIZE_OFFSET=4    # Offset 4: totalsize - total size of DTB in bytes

# Read a big-endian 32-bit value from a file
# Usage: value=$(read_be32 "$file" $offset)
read_be32() {
    local file="$1"
    local offset="$2"
    local hex
    hex=$(dd if="$file" bs=1 skip="$offset" count=4 2>/dev/null | xxd -p)
    printf "%d" "0x$hex"
}

# Check if data at offset has FDT magic
# Usage: if has_fdt_magic "$file" $offset; then ...
has_fdt_magic() {
    local file="$1"
    local offset="$2"
    local magic
    magic=$(dd if="$file" bs=1 skip="$offset" count=4 2>/dev/null | xxd -p)
    [[ "$magic" == "$FDT_MAGIC" ]]
}

# Get DTB total size from FDT header
# Usage: size=$(get_fdt_size "$file" $dtb_offset)
get_fdt_size() {
    local file="$1"
    local offset="$2"
    read_be32 "$file" $((offset + FDT_HEADER_TOTALSIZE_OFFSET))
}

# Find FDT magic within a region of a file (4-byte aligned search)
# Usage: offset=$(find_fdt_magic "$file" $start $length) || echo "not found"
# Returns: decimal offset of FDT magic, or fails if not found
find_fdt_magic() {
    local file="$1"
    local start="$2"
    local length="$3"

    # Read region and convert to hex
    local hex_dump
    hex_dump=$(dd if="$file" bs=1 skip="$start" count="$length" 2>/dev/null | xxd -p | tr -d '\n')

    # Search for FDT magic at 4-byte aligned positions
    local pos=0
    while [[ $pos -lt ${#hex_dump} ]]; do
        if [[ "${hex_dump:$pos:8}" == "$FDT_MAGIC" ]]; then
            # Convert hex position to byte offset (2 hex chars per byte)
            echo $((start + pos / 2))
            return 0
        fi
        # DTBs are 4-byte aligned, so check every 4 bytes (8 hex chars)
        pos=$((pos + 8))
    done

    return 1
}

# Extract a DTB from firmware to a file
# Usage: extract_fdt "$firmware" $offset $size "$output_file"
extract_fdt() {
    local file="$1"
    local offset="$2"
    local size="$3"
    local output="$4"

    dd if="$file" of="$output" bs=1 skip="$offset" count="$size" 2>/dev/null

    # Verify magic
    if ! has_fdt_magic "$output" 0; then
        error "Extracted file does not have valid FDT magic"
        return 1
    fi
}

# Decompile DTB to DTS using dtc
# Usage: decompile_dtb "$dtb_file" "$dts_file"
decompile_dtb() {
    local dtb_file="$1"
    local dts_file="$2"

    if dtc -I dtb -O dts -o "$dts_file" "$dtb_file" 2>/dev/null; then
        return 0
    fi

    # dtc may fail on FIT images; try with force flag
    if dtc -I dtb -O dts -f -o "$dts_file" "$dtb_file" 2>/dev/null; then
        return 0
    fi

    return 1
}
