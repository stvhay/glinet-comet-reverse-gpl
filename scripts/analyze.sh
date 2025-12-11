#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default firmware (can be overridden via argument or environment variable)
DEFAULT_FIRMWARE_URL="https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"

usage() {
    echo "Usage: $0 [OPTIONS] [FIRMWARE_URL]"
    echo ""
    echo "Analyze GL.iNet Comet (GL-RM1) firmware for GPL compliance."
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -l, --list     List known firmware versions"
    echo "  -o DIR         Output directory (default: output/)"
    echo ""
    echo "Arguments:"
    echo "  FIRMWARE_URL   URL to firmware .img file (optional)"
    echo ""
    echo "Environment Variables:"
    echo "  FIRMWARE_URL   Override firmware URL"
    echo "  OUTPUT_DIR     Override output directory"
    echo "  DOWNLOAD_DIR   Override download cache directory"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Analyze default (1.7.2)"
    echo "  $0 https://example.com/firmware.img  # Analyze specific URL"
    echo "  FIRMWARE_URL=https://... $0          # Via environment variable"
    echo ""
    echo "Known Firmware Versions:"
    list_versions
}

list_versions() {
    echo "  1.7.2 - https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
    echo ""
    echo "Note: Check https://dl.gl-inet.com/kvm/rm1/ for other versions."
}

# Parse command-line arguments
OUTPUT_DIR_ARG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -l|--list)
            echo "Known GL-RM1 Firmware Versions:"
            list_versions
            exit 0
            ;;
        -o)
            OUTPUT_DIR_ARG="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
        *)
            # Positional argument - firmware URL
            FIRMWARE_URL="$1"
            shift
            ;;
    esac
done

# Set firmware URL (priority: CLI arg > env var > default)
FIRMWARE_URL="${FIRMWARE_URL:-$DEFAULT_FIRMWARE_URL}"
FIRMWARE_FILE=$(basename "$FIRMWARE_URL")

# Extract version from filename (e.g., "1.7.2" from "glkvm-RM1-1.7.2-1128-1764344791.img")
FIRMWARE_VERSION=$(echo "$FIRMWARE_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")

# Downloads directory persists for caching; work directory is temporary
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$PROJECT_DIR/downloads}"
OUTPUT_DIR="${OUTPUT_DIR_ARG:-${OUTPUT_DIR:-$PROJECT_DIR/output}}"
WORK_DIR="$(mktemp -d)"

mkdir -p "$DOWNLOAD_DIR" "$OUTPUT_DIR"

# Ensure paths are absolute
DOWNLOAD_DIR="$(cd "$DOWNLOAD_DIR" && pwd)"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "=============================================="
echo "GL.iNet Comet (GL-RM1) Firmware Analysis"
echo "=============================================="
echo "Firmware: $FIRMWARE_FILE"
echo "Version:  $FIRMWARE_VERSION"
echo "Output:   $OUTPUT_DIR"
echo "=============================================="
echo ""

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
        # Try to get vermagic from kernel modules (most reliable)
        KERNEL_MODULE=$(find "$ROOTFS_DIR" -name "*.ko" -type f 2>/dev/null | head -1)
        if [ -n "$KERNEL_MODULE" ]; then
            VERMAGIC=$(strings "$KERNEL_MODULE" | grep -E "^vermagic=" | head -1 | sed 's/vermagic=//' || true)
            if [ -n "$VERMAGIC" ]; then
                echo "Kernel version from module vermagic:"
                echo ""
                echo '```'
                echo "$VERMAGIC"
                echo '```'
                echo ""
                # Extract just the version number
                KERNEL_VER=$(echo "$VERMAGIC" | awk '{print $1}')
                echo "**Version:** \`$KERNEL_VER\`"
            fi
        fi
        # Also check module directories
        if ls -d "$ROOTFS_DIR/lib/modules/"*/ >/dev/null 2>&1; then
            echo ""
            echo "## Module directory"
            echo ""
            echo '```'
            find "$ROOTFS_DIR/lib/modules" -maxdepth 1 -mindepth 1 -type d -exec basename {} \;
            echo '```'
        fi
        if [ -z "$VERMAGIC" ] && ! ls -d "$ROOTFS_DIR/lib/modules/"*/ >/dev/null 2>&1; then
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

    echo "=== Automated license detection ==="
    {
        echo "# Automated License Detection"
        echo ""
        echo "Automated analysis of licenses in GL.iNet Comet firmware."
        echo ""
        echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo ""

        # Function to identify license from text content
        identify_license() {
            local content="$1"
            # Check patterns in order of specificity
            if echo "$content" | grep -qi "GNU GENERAL PUBLIC LICENSE" && echo "$content" | grep -qi "Version 3"; then
                echo "GPL-3.0"
            elif echo "$content" | grep -qi "GPLv3\|GPL-3\.0\|GPL version 3"; then
                echo "GPL-3.0"
            elif echo "$content" | grep -qi "GNU GENERAL PUBLIC LICENSE" && echo "$content" | grep -qi "Version 2"; then
                echo "GPL-2.0"
            elif echo "$content" | grep -qiE "GPLv2|GPL-2\.0|GPL version 2|Licensed under GPLv2"; then
                echo "GPL-2.0"
            elif echo "$content" | grep -qi "GNU LESSER GENERAL PUBLIC LICENSE" && echo "$content" | grep -qi "Version 3"; then
                echo "LGPL-3.0"
            elif echo "$content" | grep -qiE "LGPLv3|LGPL-3\.0|LGPL version 3"; then
                echo "LGPL-3.0"
            elif echo "$content" | grep -qi "GNU LESSER GENERAL PUBLIC LICENSE" && echo "$content" | grep -qi "Version 2\.1"; then
                echo "LGPL-2.1"
            elif echo "$content" | grep -qiE "LGPLv2\.1|LGPL-2\.1|LGPL version 2\.1"; then
                echo "LGPL-2.1"
            elif echo "$content" | grep -qi "GNU LESSER GENERAL PUBLIC LICENSE"; then
                echo "LGPL"
            elif echo "$content" | grep -qi "GNU LIBRARY GENERAL PUBLIC LICENSE"; then
                echo "LGPL-2.0"
            elif echo "$content" | grep -qi "Mozilla Public License.*2\.0\|MPL-2\.0"; then
                echo "MPL-2.0"
            elif echo "$content" | grep -qi "Apache License.*2\.0\|Apache-2\.0"; then
                echo "Apache-2.0"
            elif echo "$content" | grep -qi "Permission is hereby granted, free of charge"; then
                echo "MIT"
            elif echo "$content" | grep -qi "BSD-3-Clause\|BSD 3-Clause"; then
                echo "BSD-3-Clause"
            elif echo "$content" | grep -qi "BSD-2-Clause\|BSD 2-Clause\|Simplified BSD"; then
                echo "BSD-2-Clause"
            elif echo "$content" | grep -qi "Redistribution and use in source and binary forms"; then
                echo "BSD"
            elif echo "$content" | grep -qi "ISC License\|ISC license"; then
                echo "ISC"
            elif echo "$content" | grep -qi "zlib License\|zlib/libpng"; then
                echo "Zlib"
            elif echo "$content" | grep -qi "Public Domain\|public domain\|CC0"; then
                echo "Public-Domain"
            elif echo "$content" | grep -qi "Boost Software License"; then
                echo "BSL-1.0"
            elif echo "$content" | grep -qi "OpenSSL License"; then
                echo "OpenSSL"
            else
                echo "Unknown"
            fi
        }

        # Categorize license type
        categorize_license() {
            local license="$1"
            case "$license" in
                GPL-2.0|GPL-3.0|LGPL-2.0|LGPL-2.1|LGPL-3.0|LGPL|MPL-2.0)
                    echo "Copyleft"
                    ;;
                MIT|BSD|BSD-2-Clause|BSD-3-Clause|ISC|Zlib|Apache-2.0|BSL-1.0|OpenSSL|Public-Domain)
                    echo "Permissive"
                    ;;
                *)
                    echo "Unknown"
                    ;;
            esac
        }

        # Check if license requires source disclosure
        requires_source() {
            local license="$1"
            case "$license" in
                GPL-2.0|GPL-3.0)
                    echo "Yes (full)"
                    ;;
                LGPL-2.0|LGPL-2.1|LGPL-3.0|LGPL)
                    echo "Yes (library only)"
                    ;;
                MPL-2.0)
                    echo "Yes (modified files)"
                    ;;
                *)
                    echo "No"
                    ;;
            esac
        }

        # Known library licenses (for libraries without embedded license info)
        declare -A KNOWN_LICENSES
        KNOWN_LICENSES["libc-"]="LGPL-2.1"
        KNOWN_LICENSES["libpthread"]="LGPL-2.1"
        KNOWN_LICENSES["libm-"]="LGPL-2.1"
        KNOWN_LICENSES["libdl-"]="LGPL-2.1"
        KNOWN_LICENSES["librt-"]="LGPL-2.1"
        KNOWN_LICENSES["libresolv"]="LGPL-2.1"
        KNOWN_LICENSES["libnsl"]="LGPL-2.1"
        KNOWN_LICENSES["libnss"]="LGPL-2.1"
        KNOWN_LICENSES["libcrypt-"]="LGPL-2.1"
        KNOWN_LICENSES["libutil-"]="LGPL-2.1"
        KNOWN_LICENSES["ld-"]="LGPL-2.1"
        KNOWN_LICENSES["libstdc++"]="GPL-3.0-with-GCC-exception"
        KNOWN_LICENSES["libgcc"]="GPL-3.0-with-GCC-exception"
        KNOWN_LICENSES["libatomic"]="GPL-3.0-with-GCC-exception"
        KNOWN_LICENSES["libssl"]="OpenSSL"
        KNOWN_LICENSES["libcrypto"]="OpenSSL"
        KNOWN_LICENSES["libz.so"]="Zlib"
        KNOWN_LICENSES["libpng"]="Zlib"
        KNOWN_LICENSES["libjpeg"]="IJG"
        KNOWN_LICENSES["libsqlite"]="Public-Domain"
        KNOWN_LICENSES["libexpat"]="MIT"
        KNOWN_LICENSES["libcurl"]="MIT"
        KNOWN_LICENSES["libevent"]="BSD-3-Clause"
        KNOWN_LICENSES["libpcre"]="BSD-3-Clause"
        KNOWN_LICENSES["libffi"]="MIT"
        KNOWN_LICENSES["liblzma"]="Public-Domain"
        KNOWN_LICENSES["libgmp"]="LGPL-3.0"
        KNOWN_LICENSES["libnettle"]="LGPL-3.0"
        KNOWN_LICENSES["libgnutls"]="LGPL-2.1"
        KNOWN_LICENSES["libglib"]="LGPL-2.1"
        KNOWN_LICENSES["libgio"]="LGPL-2.1"
        KNOWN_LICENSES["libgobject"]="LGPL-2.1"
        KNOWN_LICENSES["libgmodule"]="LGPL-2.1"
        KNOWN_LICENSES["libgthread"]="LGPL-2.1"
        KNOWN_LICENSES["libdbus"]="GPL-2.0"
        KNOWN_LICENSES["libbluetooth"]="GPL-2.0"
        KNOWN_LICENSES["libasound"]="LGPL-2.1"
        KNOWN_LICENSES["libavcodec"]="LGPL-2.1"
        KNOWN_LICENSES["libavformat"]="LGPL-2.1"
        KNOWN_LICENSES["libavutil"]="LGPL-2.1"
        KNOWN_LICENSES["libavfilter"]="LGPL-2.1"
        KNOWN_LICENSES["libavdevice"]="LGPL-2.1"
        KNOWN_LICENSES["libswscale"]="LGPL-2.1"
        KNOWN_LICENSES["libswresample"]="LGPL-2.1"
        KNOWN_LICENSES["libmad"]="GPL-2.0"
        KNOWN_LICENSES["libogg"]="BSD-3-Clause"
        KNOWN_LICENSES["libopus"]="BSD-3-Clause"
        KNOWN_LICENSES["libspeex"]="BSD-3-Clause"
        KNOWN_LICENSES["libreadline"]="GPL-3.0"
        KNOWN_LICENSES["libncurses"]="MIT"
        KNOWN_LICENSES["librockchip_mpp"]="Apache-2.0"
        KNOWN_LICENSES["librga"]="Apache-2.0"
        KNOWN_LICENSES["libeasymedia"]="Apache-2.0"
        KNOWN_LICENSES["liblua"]="MIT"
        KNOWN_LICENSES["libjansson"]="MIT"
        KNOWN_LICENSES["libjson-c"]="MIT"
        KNOWN_LICENSES["libxml2"]="MIT"
        KNOWN_LICENSES["libxslt"]="MIT"
        KNOWN_LICENSES["libnl"]="LGPL-2.1"
        KNOWN_LICENSES["libmnl"]="LGPL-2.1"
        KNOWN_LICENSES["libdrm"]="MIT"
        KNOWN_LICENSES["libpython"]="PSF-2.0"
        KNOWN_LICENSES["libboost"]="BSL-1.0"

        # Arrays to track results
        declare -a COPYLEFT_COMPONENTS=()
        declare -a PERMISSIVE_COMPONENTS=()
        declare -a UNKNOWN_COMPONENTS=()

        echo "## License Detection Methods"
        echo ""
        echo "1. **Binary string extraction** - Search for license text in executables"
        echo "2. **Python package metadata** - Parse \`*.dist-info/METADATA\` files"
        echo "3. **License file analysis** - Identify license type from COPYING/LICENSE files"
        echo "4. **Known library lookup** - Cross-reference against known open source licenses"
        echo ""

        # =====================================================
        # Section 1: Binary License Strings
        # =====================================================
        echo "## Binary License Strings"
        echo ""
        echo "License information extracted from executable binaries:"
        echo ""
        echo "| Binary | License String | Detected License |"
        echo "|--------|----------------|------------------|"

        # Check key binaries for license strings
        for bin_path in "$ROOTFS_DIR/bin/busybox" "$ROOTFS_DIR/usr/bin/coreutils" "$ROOTFS_DIR/usr/bin/bash" "$ROOTFS_DIR/usr/bin/gdb" "$ROOTFS_DIR/usr/bin/vim"; do
            if [ -f "$bin_path" ]; then
                bin_name=$(basename "$bin_path")
                # Use more specific patterns to avoid false positives
                license_str=$(strings "$bin_path" 2>/dev/null | grep -iE "licensed under|GNU General Public|GNU Lesser|GPLv[23]|LGPLv|BSD License|MIT License|Apache License" | head -1 | cut -c1-60 || true)
                if [ -n "$license_str" ]; then
                    detected=$(identify_license "$license_str")
                    echo "| \`$bin_name\` | ${license_str}... | $detected |"
                fi
            fi
        done
        echo ""

        # =====================================================
        # Section 2: Python Package Metadata
        # =====================================================
        echo "## Python Package Licenses"
        echo ""
        echo "Licenses from Python package metadata (\`*.dist-info/METADATA\`):"
        echo ""
        echo "| Package | Version | License |"
        echo "|---------|---------|---------|"

        PYTHON_PKGS=$(find "$ROOTFS_DIR" -path "*/dist-info/METADATA" -type f 2>/dev/null | head -50 || true)
        if [ -n "$PYTHON_PKGS" ]; then
            while IFS= read -r metadata_file; do
                pkg_name=$(grep -E "^Name:" "$metadata_file" 2>/dev/null | head -1 | sed 's/Name: *//' || true)
                pkg_ver=$(grep -E "^Version:" "$metadata_file" 2>/dev/null | head -1 | sed 's/Version: *//' || true)
                pkg_license=$(grep -E "^License:" "$metadata_file" 2>/dev/null | head -1 | sed 's/License: *//' || true)
                if [ -n "$pkg_name" ]; then
                    echo "| $pkg_name | $pkg_ver | $pkg_license |"
                    # Categorize
                    detected=$(identify_license "$pkg_license")
                    category=$(categorize_license "$detected")
                    if [ "$category" = "Copyleft" ]; then
                        COPYLEFT_COMPONENTS+=("Python: $pkg_name ($detected)")
                    elif [ "$category" = "Permissive" ]; then
                        PERMISSIVE_COMPONENTS+=("Python: $pkg_name ($detected)")
                    fi
                fi
            done <<< "$PYTHON_PKGS"
        else
            echo "| *No Python packages found* | - | - |"
        fi
        echo ""

        # =====================================================
        # Section 3: License File Analysis
        # =====================================================
        echo "## License File Analysis"
        echo ""
        echo "License types identified from LICENSE/COPYING file contents:"
        echo ""
        echo "| File | Detected License | Category |"
        echo "|------|------------------|----------|"

        LICENSE_FILE_LIST=$(find "$ROOTFS_DIR" \( -iname "COPYING*" -o -iname "LICENSE*" \) -type f 2>/dev/null | head -30 || true)
        if [ -n "$LICENSE_FILE_LIST" ]; then
            while IFS= read -r lic_file; do
                rel_path=$(echo "$lic_file" | sed "s|$ROOTFS_DIR||")
                content=$(head -100 "$lic_file" 2>/dev/null || true)
                if [ -n "$content" ]; then
                    detected=$(identify_license "$content")
                    category=$(categorize_license "$detected")
                    echo "| \`$rel_path\` | $detected | $category |"
                    if [ "$category" = "Copyleft" ]; then
                        COPYLEFT_COMPONENTS+=("File: $rel_path ($detected)")
                    fi
                fi
            done <<< "$LICENSE_FILE_LIST"
        else
            echo "| *No license files found* | - | - |"
        fi
        echo ""

        # =====================================================
        # Section 4: Shared Library License Lookup
        # =====================================================
        echo "## Shared Library Licenses"
        echo ""
        echo "Licenses for shared libraries (from known database):"
        echo ""
        echo "| Library | License | Category | Source Disclosure |"
        echo "|---------|---------|----------|-------------------|"

        SO_FILES=$(find "$ROOTFS_DIR" -name "*.so*" -type f 2>/dev/null | head -100 || true)
        if [ -n "$SO_FILES" ]; then
            while IFS= read -r so_file; do
                lib_name=$(basename "$so_file")
                detected_license=""

                # Check against known licenses
                for pattern in "${!KNOWN_LICENSES[@]}"; do
                    if [[ "$lib_name" == *"$pattern"* ]]; then
                        detected_license="${KNOWN_LICENSES[$pattern]}"
                        break
                    fi
                done

                if [ -n "$detected_license" ]; then
                    category=$(categorize_license "$detected_license")
                    disclosure=$(requires_source "$detected_license")
                    echo "| \`$lib_name\` | $detected_license | $category | $disclosure |"

                    if [ "$category" = "Copyleft" ]; then
                        COPYLEFT_COMPONENTS+=("Library: $lib_name ($detected_license)")
                    elif [ "$category" = "Permissive" ]; then
                        PERMISSIVE_COMPONENTS+=("Library: $lib_name ($detected_license)")
                    fi
                fi
            done <<< "$SO_FILES"
        fi
        echo ""

        # =====================================================
        # Section 5: Summary
        # =====================================================
        echo "## Summary"
        echo ""
        echo "### Components Requiring Source Disclosure"
        echo ""
        echo "The following components are under copyleft licenses and require source code disclosure:"
        echo ""

        # Deduplicate and list copyleft components
        if [ ${#COPYLEFT_COMPONENTS[@]} -gt 0 ]; then
            printf '%s\n' "${COPYLEFT_COMPONENTS[@]}" | sort -u | while read -r comp; do
                echo "- $comp"
            done
        else
            echo "*None detected*"
        fi
        echo ""

        echo "### License Category Counts"
        echo ""
        copyleft_count=$(printf '%s\n' "${COPYLEFT_COMPONENTS[@]}" 2>/dev/null | sort -u | wc -l | tr -d ' ')
        permissive_count=$(printf '%s\n' "${PERMISSIVE_COMPONENTS[@]}" 2>/dev/null | sort -u | wc -l | tr -d ' ')
        echo "| Category | Count |"
        echo "|----------|-------|"
        echo "| Copyleft (GPL, LGPL, MPL) | $copyleft_count |"
        echo "| Permissive (MIT, BSD, Apache) | $permissive_count |"
        echo ""

        echo "### Source Disclosure Requirements"
        echo ""
        echo "| License | Disclosure Scope |"
        echo "|---------|------------------|"
        echo "| GPL-2.0, GPL-3.0 | Complete source for derivative work |"
        echo "| LGPL-2.1, LGPL-3.0 | Library source + re-linking capability |"
        echo "| MPL-2.0 | Modified files only |"
        echo "| MIT, BSD, Apache-2.0 | None (permissive) |"
        echo ""

        echo "---"
        echo ""
        echo "*Note: This is automated detection and may not be comprehensive. Manual verification recommended for legal compliance.*"

    } > "$OUTPUT_DIR/licenses.md"
    echo "Wrote licenses.md"

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
    UBOOT_VERS=""
    UBOOT_DECOMPRESSED=""
    UBOOT_EXTRACTED=""
    UBOOT_VERS=$(strings "$WORK_DIR/$FIRMWARE_FILE" | grep -E "U-Boot [0-9]" | sort -u | head -10 || true)
    if [ -n "$UBOOT_VERS" ]; then
        echo "Version strings found in firmware:"
        echo ""
        echo '```'
        echo "$UBOOT_VERS"
        echo '```'
    fi
    # Check for decompressed binaries from binwalk extraction (typically u-boot)
    DECOMPRESSED_BINS=$(find "$WORK_DIR/$EXTRACT_DIR" -name "decompressed.bin" -type f 2>/dev/null || true)
    if [ -n "$DECOMPRESSED_BINS" ]; then
        while IFS= read -r bin_file; do
            UBOOT_DECOMPRESSED=$(strings "$bin_file" | grep -E "U-Boot 20[0-9]{2}\.[0-9]{2}" | sort -u | head -5 || true)
            if [ -n "$UBOOT_DECOMPRESSED" ]; then
                echo ""
                echo "## From decompressed binary"
                echo ""
                echo '```'
                echo "$UBOOT_DECOMPRESSED"
                echo '```'
                break
            fi
        done <<< "$DECOMPRESSED_BINS"
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
    if [ -z "$UBOOT_VERS" ] && [ -z "$UBOOT_DECOMPRESSED" ] && [ -z "$UBOOT_EXTRACTED" ]; then
        echo "*No U-Boot version string found in firmware image*"
    fi
} > "$OUTPUT_DIR/uboot-version.md"
echo "Wrote uboot-version.md"

echo "=== Extracting Device Trees ==="
{
    echo "# Device Tree Analysis"
    echo ""
    echo "Device Trees found in the firmware image."
    echo ""

    # Find all DTB files extracted by binwalk
    DTB_FILES=$(find "$WORK_DIR/$EXTRACT_DIR" -name "*.dtb" -type f 2>/dev/null | sort || true)

    if [ -n "$DTB_FILES" ]; then
        DTB_COUNT=0
        while IFS= read -r dtb_file; do
            DTB_COUNT=$((DTB_COUNT + 1))
            dtb_name=$(basename "$dtb_file")
            dtb_offset=$(basename "$(dirname "$dtb_file")" | grep -oE "^[0-9A-Fa-f]+" || echo "unknown")

            echo "## DTB #$DTB_COUNT: \`$dtb_name\` (offset 0x$dtb_offset)"
            echo ""

            # Get basic info
            dtb_size=$(stat -f%z "$dtb_file" 2>/dev/null || stat -c%s "$dtb_file" 2>/dev/null || echo "unknown")
            echo "- **Size:** $dtb_size bytes"

            # Check if file is binary DTB or already decompiled DTS
            file_type=$(file "$dtb_file")
            if echo "$file_type" | grep -q "ASCII text"; then
                # Already decompiled to DTS by binwalk
                DTS_CONTENT=$(cat "$dtb_file")
            else
                # Binary DTB, need to decompile
                DTS_CONTENT=$(dtc -I dtb -O dts "$dtb_file" 2>/dev/null || echo "")
            fi

            if [ -z "$DTS_CONTENT" ]; then
                echo "- **Type:** Could not parse"
                echo ""
                continue
            fi

            # Determine type based on content
            if echo "$DTS_CONTENT" | grep -q "u-boot,dm-"; then
                echo "- **Type:** U-Boot Device Tree"
            elif echo "$DTS_CONTENT" | grep -q "description.*FIT"; then
                echo "- **Type:** FIT Image (Flattened Image Tree)"
            elif echo "$DTS_CONTENT" | grep -q "linux,"; then
                echo "- **Type:** Linux Kernel Device Tree"
            else
                echo "- **Type:** Device Tree"
            fi

            # Extract model and compatible strings
            MODEL=$(echo "$DTS_CONTENT" | grep -E "^\s*model\s*=" | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/' || true)
            COMPAT=$(echo "$DTS_CONTENT" | grep -E "^\s*compatible\s*=" | head -1 | sed 's/.*= *"\([^"]*\)".*/\1/' || true)

            if [ -n "$MODEL" ]; then
                echo "- **Model:** $MODEL"
            fi
            if [ -n "$COMPAT" ]; then
                echo "- **Compatible:** \`$COMPAT\`"
            fi

            # Check if this is a FIT image (contains images/configurations nodes)
            if echo "$DTS_CONTENT" | grep -q "description.*FIT"; then
                echo ""
                echo "### FIT Image Contents"
                echo ""
                echo '```'
                echo "$DTS_CONTENT" | grep -E "^\s*(description|type|arch|os|compression)\s*=" | head -20 || true
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
echo "Wrote device-trees.md"

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
    echo "| Version | $FIRMWARE_VERSION |"
    echo "| Filename | \`$FIRMWARE_FILE\` |"
    echo "| URL | $FIRMWARE_URL |"
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
    echo "| [device-trees.md](device-trees.md) | Device Tree Blob analysis |"
    echo "| [gpl-binaries.md](gpl-binaries.md) | GPL-licensed binaries found |"
    echo "| [kernel-modules.md](kernel-modules.md) | Kernel modules (.ko files) |"
    echo "| [kernel-version.md](kernel-version.md) | Linux kernel version |"
    echo "| [license-files.md](license-files.md) | License files in filesystem |"
    echo "| [licenses.md](licenses.md) | Automated license detection |"
    echo "| [packages.md](packages.md) | Shared libraries |"
    echo "| [uboot-version.md](uboot-version.md) | U-Boot bootloader info |"
} > "$OUTPUT_DIR/SUMMARY.md"
cat "$OUTPUT_DIR/SUMMARY.md"

echo ""
echo "=== Analysis complete ==="
ls -la "$OUTPUT_DIR"
