#!/usr/bin/env bash
set -euo pipefail

# Extract eMMC partitions from GL.iNet Comet device via SSH
# WARNING: This script only performs READ operations on the device
# No data is written to the device

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_DIR/config.env}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/partitions}"

# Load configuration
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    echo "Copy config.env.template to config.env and fill in your device details"
    exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [ -z "${DEVICE_PASSWORD:-}" ]; then
    echo "Error: DEVICE_PASSWORD not set in config.env"
    exit 1
fi

if [ -z "${DEVICE_IP:-}" ]; then
    echo "Error: DEVICE_IP not set in config.env"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# SSH options for non-interactive use
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

echo "=== GL.iNet Comet Partition Extractor ==="
echo "Device: root@$DEVICE_IP"
echo "Output: $OUTPUT_DIR"
echo ""
echo "WARNING: This script performs READ-ONLY operations on the device."
echo ""

# Function to run command on device (read-only commands only)
remote_cmd() {
    sshpass -p "$DEVICE_PASSWORD" ssh "${SSH_OPTS[@]}" "root@$DEVICE_IP" "$@"
}

# Function to copy file from device
remote_copy() {
    local src="$1"
    local dst="$2"
    sshpass -p "$DEVICE_PASSWORD" scp "${SSH_OPTS[@]}" "root@$DEVICE_IP:$src" "$dst"
}

echo "=== Testing connection ==="
if ! remote_cmd "echo 'Connection successful'"; then
    echo "Error: Cannot connect to device"
    exit 1
fi

echo ""
echo "=== Reading partition table ==="
remote_cmd "cat /proc/partitions" | tee "$OUTPUT_DIR/partitions.txt"

echo ""
echo "=== Reading mount points ==="
remote_cmd "mount" | tee "$OUTPUT_DIR/mounts.txt"

echo ""
echo "=== Extracting partitions ==="

# Identify partition content type from magic bytes
# Returns: description string based on content analysis
identify_partition_content() {
    local file="$1"
    local magic

    # Read first 16 bytes as hex
    magic=$(xxd -l 16 -p "$file" 2>/dev/null || echo "")

    case "$magic" in
        d00dfeed*)
            # FDT/DTB magic - could be FIT image or device tree
            if strings "$file" 2>/dev/null | grep -q "U-Boot"; then
                echo "fit-uboot"
            elif strings "$file" 2>/dev/null | grep -q "linux,initrd"; then
                echo "fit-kernel"
            else
                echo "dtb"
            fi
            ;;
        68737173*)
            echo "squashfs"  # "hsqs" in ASCII
            ;;
        ubi#*)
            echo "ubifs"
            ;;
        53ef*)
            echo "ext4"  # ext2/3/4 superblock at offset 0x438
            ;;
        1f8b*)
            echo "gzip"
            ;;
        *)
            # Check for ext4 at standard superblock offset (0x438)
            local sb_magic
            sb_magic=$(xxd -s 0x438 -l 2 -p "$file" 2>/dev/null || echo "")
            if [[ "$sb_magic" == "53ef" ]]; then
                echo "ext4"
            elif [[ -z "$magic" ]] || [[ "$magic" =~ ^0+$ ]]; then
                echo "empty"
            else
                echo "unknown"
            fi
            ;;
    esac
}

# Partitions to extract (descriptions determined by content analysis after extraction)
PARTITIONS=(
    "mmcblk0p1"
    "mmcblk0p2"
    "mmcblk0p3"
    "mmcblk0p4"
    "mmcblk0p5"
    "mmcblk0p6"
    "mmcblk0p7"
    "mmcblk0p8"
    "mmcblk0p9"
    "mmcblk0p10"
)

for part in "${PARTITIONS[@]}"; do
    device="/dev/$part"
    output_file="$OUTPUT_DIR/$part.bin"

    echo ""
    echo "--- Extracting $part ---"

    # Check if partition exists
    if ! remote_cmd "test -b $device" 2>/dev/null; then
        echo "Skipping $part: device not found"
        continue
    fi

    # Get partition size
    size_blocks=$(remote_cmd "cat /sys/class/block/$part/size" 2>/dev/null || echo "0")
    size_bytes=$((size_blocks * 512))
    size_mb=$((size_bytes / 1024 / 1024))

    echo "Size: ${size_mb}MB ($size_bytes bytes)"

    if [ "$size_bytes" -eq 0 ]; then
        echo "Skipping $part: zero size"
        continue
    fi

    # Extract partition using dd over ssh (READ ONLY)
    echo "Extracting to $output_file..."
    remote_cmd "dd if=$device bs=1M" > "$output_file" 2>/dev/null

    # Verify size
    local_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
    echo "Extracted: $local_size bytes"

    if [ "$local_size" -ne "$size_bytes" ]; then
        echo "WARNING: Size mismatch! Expected $size_bytes, got $local_size"
    fi
done

echo ""
echo "=== Analyzing partition contents ==="
echo ""
echo "| Partition | Size | Content Type |"
echo "|-----------|------|--------------|"

for part in "${PARTITIONS[@]}"; do
    output_file="$OUTPUT_DIR/$part.bin"
    if [[ -f "$output_file" ]]; then
        local_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
        size_mb=$((local_size / 1024 / 1024))
        content_type=$(identify_partition_content "$output_file")
        echo "| $part | ${size_mb}MB | $content_type |"
    fi
done

echo ""
echo "=== Extraction complete ==="
echo "Files written to: $OUTPUT_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f -name "*.bin" -printf "  %f (%s bytes)\n" 2>/dev/null || \
    find "$OUTPUT_DIR" -maxdepth 1 -type f -name "*.bin" -exec stat -f "  %N (%z bytes)" {} \;
