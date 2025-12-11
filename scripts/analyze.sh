#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

FIRMWARE_URL="https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
FIRMWARE_FILE="glkvm-RM1-1.7.2-1128-1764344791.img"

# Downloads directory persists for caching; work directory is temporary
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$PROJECT_DIR/downloads}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/output}"
WORK_DIR="$(mktemp -d)"

mkdir -p "$DOWNLOAD_DIR" "$OUTPUT_DIR"

# Ensure paths are absolute
DOWNLOAD_DIR="$(cd "$DOWNLOAD_DIR" && pwd)"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "=== Downloading firmware ==="
if [ -f "$DOWNLOAD_DIR/$FIRMWARE_FILE" ]; then
    echo "Using cached firmware: $DOWNLOAD_DIR/$FIRMWARE_FILE"
else
    curl -L -o "$DOWNLOAD_DIR/$FIRMWARE_FILE" "$FIRMWARE_URL"
fi

# Copy to work directory for extraction
cp "$DOWNLOAD_DIR/$FIRMWARE_FILE" "$WORK_DIR/"

echo "=== Firmware file info ==="
file "$WORK_DIR/$FIRMWARE_FILE"

echo "=== Binwalk analysis ==="
{
    echo "# Binwalk Analysis"
    echo ""
    echo '```'
    binwalk "$WORK_DIR/$FIRMWARE_FILE"
    echo '```'
} > "$OUTPUT_DIR/binwalk-scan.md"
echo "Wrote binwalk-scan.md"

echo "=== Extracting firmware ==="
cd "$WORK_DIR"
# binwalk may return non-zero if some extractions fail, but partial extraction is still useful
binwalk -e "$FIRMWARE_FILE" || echo "Warning: binwalk extraction had errors (partial extraction may still be usable)"

# binwalk extracts to extractions/<filename>.extracted/
EXTRACT_DIR="extractions/${FIRMWARE_FILE}.extracted"

echo "=== Analyzing extracted contents ==="
if [ -d "$EXTRACT_DIR" ]; then
    {
        echo "# Extracted Files"
        echo ""
        echo "First 100 files identified by \`file\` command:"
        echo ""
        echo '```'
        find "$EXTRACT_DIR" -type f -exec file {} \; 2>/dev/null | head -100
        echo '```'
    } > "$OUTPUT_DIR/extracted-files.md"
    echo "Wrote extracted-files.md"
fi

echo "=== Looking for SquashFS root filesystem ==="
# binwalk auto-extracts squashfs to squashfs-root directory
ROOTFS_DIR=$(find "$WORK_DIR" -type d -name "squashfs-root" 2>/dev/null | head -1 || true)

if [ -n "$ROOTFS_DIR" ] && [ -d "$ROOTFS_DIR" ]; then
    echo "Found extracted rootfs: $ROOTFS_DIR"

    echo "=== Listing kernel modules ==="
    {
        echo "# Kernel Modules"
        echo ""
        echo "These \`.ko\` files are GPL-licensed. Source code must be provided under GPL."
        echo ""
        MODULE_LIST=$(find "$ROOTFS_DIR" -name "*.ko" 2>/dev/null | sed "s|$ROOTFS_DIR||" | sort)
        if [ -n "$MODULE_LIST" ]; then
            echo '```'
            echo "$MODULE_LIST"
            echo '```'
        else
            echo "*No kernel modules found*"
        fi
    } > "$OUTPUT_DIR/kernel-modules.md"
    echo "Wrote kernel-modules.md"

    echo "=== Extracting kernel version ==="
    {
        echo "# Kernel Version"
        echo ""
        # List module directories which contain kernel version
        if ls -d "$ROOTFS_DIR/lib/modules/"*/ >/dev/null 2>&1; then
            echo "Kernel version from module directory:"
            echo ""
            echo '```'
            find "$ROOTFS_DIR/lib/modules" -maxdepth 1 -mindepth 1 -type d -exec basename {} \;
            echo '```'
        else
            echo "*Could not determine kernel version*"
        fi
    } > "$OUTPUT_DIR/kernel-version.md"
    echo "Wrote kernel-version.md"

    echo "=== Listing GPL-licensed binaries ==="
    {
        echo "# GPL-Licensed Binaries"
        echo ""
        echo "## BusyBox"
        echo ""
        if [ -f "$ROOTFS_DIR/bin/busybox" ]; then
            echo '```'
            ls -la "$ROOTFS_DIR/bin/busybox"
            file "$ROOTFS_DIR/bin/busybox"
            echo '```'
            echo ""
            BUSYBOX_VER=$(strings "$ROOTFS_DIR/bin/busybox" | grep -i "busybox v" | head -1 || true)
            if [ -n "$BUSYBOX_VER" ]; then
                echo "**Version:** \`$BUSYBOX_VER\`"
            else
                echo "*Version string not found*"
            fi
        else
            echo "*Not found*"
        fi
        echo ""
        echo "## GNU Coreutils"
        echo ""
        if [ -f "$ROOTFS_DIR/usr/bin/coreutils" ]; then
            echo '```'
            ls -la "$ROOTFS_DIR/usr/bin/coreutils"
            file "$ROOTFS_DIR/usr/bin/coreutils"
            echo '```'
        else
            echo "*Not found as standalone binary*"
        fi
        echo ""
        echo "## Other GPL Tools"
        echo ""
        echo "| Tool | Found |"
        echo "|------|-------|"
        for bin in bash gzip tar grep sed awk vim; do
            if [ -f "$ROOTFS_DIR/usr/bin/$bin" ] || [ -f "$ROOTFS_DIR/bin/$bin" ]; then
                echo "| $bin | Yes |"
            else
                echo "| $bin | No |"
            fi
        done
    } > "$OUTPUT_DIR/gpl-binaries.md"
    echo "Wrote gpl-binaries.md"

    echo "=== Searching for license files ==="
    {
        echo "# License Files"
        echo ""
        echo "License files found in the root filesystem:"
        echo ""
        LICENSE_FILES=$(find "$ROOTFS_DIR" \( -iname "COPYING*" -o -iname "LICENSE*" -o -iname "GPL*" \) 2>/dev/null | sed "s|$ROOTFS_DIR||" | sort)
        if [ -n "$LICENSE_FILES" ]; then
            echo '```'
            echo "$LICENSE_FILES"
            echo '```'
        else
            echo "*No license files found*"
        fi
    } > "$OUTPUT_DIR/license-files.md"
    echo "Wrote license-files.md"

    echo "=== Extracting build information ==="
    {
        echo "# Build Information"
        echo ""
        echo "## OS Release"
        echo ""
        if [ -f "$ROOTFS_DIR/etc/os-release" ]; then
            echo '```'
            cat "$ROOTFS_DIR/etc/os-release"
            echo '```'
        else
            echo "*Not found*"
        fi
        echo ""
        echo "## Version Files"
        echo ""
        for f in version buildinfo glinet_release fw_version; do
            if [ -f "$ROOTFS_DIR/etc/$f" ]; then
                echo "### /etc/$f"
                echo ""
                echo '```'
                cat "$ROOTFS_DIR/etc/$f"
                echo '```'
                echo ""
            fi
        done
    } > "$OUTPUT_DIR/build-info.md"
    echo "Wrote build-info.md"

    echo "=== Package listing ==="
    {
        echo "# Shared Libraries"
        echo ""
        echo "Shared libraries found in the root filesystem (first 200):"
        echo ""
        echo '```'
        find "$ROOTFS_DIR" -name "*.so*" -type f 2>/dev/null | sed "s|$ROOTFS_DIR||" | sort | head -200
        echo '```'
    } > "$OUTPUT_DIR/packages.md"
    echo "Wrote packages.md"
else
    echo "No SquashFS filesystem found or extraction failed"
fi

echo "=== Searching for U-Boot version ==="
{
    echo "# U-Boot Information"
    echo ""
    UBOOT_VERS=$(strings "$WORK_DIR/$FIRMWARE_FILE" | grep -E "U-Boot [0-9]" | sort -u | head -10 || true)
    if [ -n "$UBOOT_VERS" ]; then
        echo "Version strings found in firmware:"
        echo ""
        echo '```'
        echo "$UBOOT_VERS"
        echo '```'
    else
        echo "*No U-Boot version string found in firmware image*"
    fi
    # Also check extracted u-boot binary
    UBOOT_BIN=$(find "$WORK_DIR/$EXTRACT_DIR" -name "u-boot-nodtb.bin" 2>/dev/null | head -1 || true)
    if [ -n "$UBOOT_BIN" ] && [ -f "$UBOOT_BIN" ]; then
        echo ""
        echo "## From extracted u-boot-nodtb.bin"
        echo ""
        UBOOT_EXTRACTED=$(strings "$UBOOT_BIN" | grep -E "U-Boot [0-9]|20[0-9]{2}\.[0-9]{2}" | sort -u | head -10 || true)
        if [ -n "$UBOOT_EXTRACTED" ]; then
            echo '```'
            echo "$UBOOT_EXTRACTED"
            echo '```'
        else
            echo "*No version string found*"
        fi
    fi
} > "$OUTPUT_DIR/uboot-version.md"
echo "Wrote uboot-version.md"

echo "=== Generating Summary ==="
{
    echo "# GPL Compliance Analysis Summary"
    echo ""
    echo "**GL.iNet Comet (RM1) Firmware**"
    echo ""
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    echo "## Firmware Source"
    echo ""
    echo "| Property | Value |"
    echo "|----------|-------|"
    echo "| URL | $FIRMWARE_URL |"
    echo "| Filename | \`$FIRMWARE_FILE\` |"
    echo ""
    echo "## GPL Components Identified"
    echo ""
    echo "### Build System"
    echo ""
    if [ -f "$OUTPUT_DIR/build-info.md" ]; then
        # Extract key info
        grep -E "^(NAME|VERSION|PRETTY_NAME)=" "$ROOTFS_DIR/etc/os-release" 2>/dev/null | while read -r line; do
            echo "- $line"
        done || echo "*See build-info.md*"
    fi
    echo ""
    echo "### Kernel"
    echo ""
    if [ -f "$OUTPUT_DIR/kernel-modules.md" ]; then
        MODULE_COUNT=$(find "$ROOTFS_DIR" -name "*.ko" 2>/dev/null | wc -l | tr -d ' ')
        echo "- **$MODULE_COUNT** kernel modules found"
        echo "- See [kernel-modules.md](kernel-modules.md) for full list"
    fi
    echo ""
    echo "### GPL Binaries"
    echo ""
    if [ -f "$ROOTFS_DIR/bin/busybox" ]; then
        BUSYBOX_VER=$(strings "$ROOTFS_DIR/bin/busybox" | grep -i "busybox v" | head -1 || echo "unknown")
        echo "- **BusyBox**: \`$BUSYBOX_VER\`"
    fi
    echo "- See [gpl-binaries.md](gpl-binaries.md) for full list"
    echo ""
    echo "## Output Files"
    echo ""
    echo "| File | Description |"
    echo "|------|-------------|"
    echo "| [binwalk-scan.md](binwalk-scan.md) | Firmware structure analysis |"
    echo "| [build-info.md](build-info.md) | OS and version information |"
    echo "| [gpl-binaries.md](gpl-binaries.md) | GPL-licensed binaries found |"
    echo "| [kernel-modules.md](kernel-modules.md) | Kernel modules (.ko files) |"
    echo "| [kernel-version.md](kernel-version.md) | Linux kernel version |"
    echo "| [license-files.md](license-files.md) | License files in filesystem |"
    echo "| [packages.md](packages.md) | Shared libraries |"
    echo "| [uboot-version.md](uboot-version.md) | U-Boot bootloader info |"
} > "$OUTPUT_DIR/SUMMARY.md"
cat "$OUTPUT_DIR/SUMMARY.md"

echo ""
echo "=== Analysis complete ==="
ls -la "$OUTPUT_DIR"
