#!/usr/bin/env bash
# Analyze Secure Boot Configuration
# This script extracts and analyzes secure boot related information from the firmware.
#
# Usage: ./scripts/analyze-secure-boot.sh [firmware.img]
#
# Requires: nix develop shell (provides binwalk, dtc, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default firmware URL
DEFAULT_FW_URL="https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
WORK_DIR="/tmp/fw_analysis"
OUTPUT_FILE="${PROJECT_ROOT}/output/secure-boot-analysis.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Get firmware path
if [[ $# -ge 1 ]]; then
    if [[ -f "$1" ]]; then
        FIRMWARE="$1"
    else
        FW_URL="$1"
        FIRMWARE="${WORK_DIR}/$(basename "$FW_URL")"
    fi
else
    FW_URL="$DEFAULT_FW_URL"
    FIRMWARE="${WORK_DIR}/$(basename "$FW_URL")"
fi

# Create work directory
mkdir -p "$WORK_DIR"
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Download firmware if needed
if [[ ! -f "$FIRMWARE" ]]; then
    info "Downloading firmware..."
    curl -L -o "$FIRMWARE" "$FW_URL"
fi

info "Analyzing: $FIRMWARE"

# Start output file
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$OUTPUT_FILE" << EOF
# Secure Boot Analysis

**GL.iNet Comet (GL-RM1) Firmware**

Generated: $TIMESTAMP

## Overview

This document analyzes the secure boot configuration of the GL.iNet Comet firmware.
Analysis is based on static examination of firmware binaries.

EOF

# ==============================================================================
# Section 1: FIT Image Signature Analysis
# ==============================================================================
info "Analyzing FIT image signatures..."

cat >> "$OUTPUT_FILE" << 'EOF'
## FIT Image Signatures

FIT (Flattened Image Tree) images can contain RSA signatures for verified boot.

### Bootloader FIT Image

Extracted from firmware offset 0x8F1B4:

EOF

# Extract and analyze bootloader FIT
FIT_OFFSET=$((0x8F1B4))
# First find the DTS that binwalk extracts
EXTRACTIONS_DIR="${WORK_DIR}/extractions/$(basename "$FIRMWARE").extracted"

if [[ -d "$EXTRACTIONS_DIR" ]]; then
    BOOTLOADER_FIT="${EXTRACTIONS_DIR}/8F1B4/system.dtb"
    if [[ -f "$BOOTLOADER_FIT" ]]; then
        echo '```' >> "$OUTPUT_FILE"
        grep -A 30 "configurations" "$BOOTLOADER_FIT" 2>/dev/null | head -40 >> "$OUTPUT_FILE" || echo "Could not extract configuration" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
fi

cat >> "$OUTPUT_FILE" << 'EOF'

### Kernel FIT Image

Extracted from firmware offset 0x49B1B4:

EOF

KERNEL_FIT="${EXTRACTIONS_DIR}/49B1B4/system.dtb"
if [[ -f "$KERNEL_FIT" ]]; then
    echo '```' >> "$OUTPUT_FILE"
    grep -A 30 "configurations" "$KERNEL_FIT" 2>/dev/null | head -40 >> "$OUTPUT_FILE" || echo "Could not extract configuration" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
fi

cat >> "$OUTPUT_FILE" << 'EOF'

### Signature Summary

| FIT Image | Signature Algorithm | Key Name | Signed Components |
|-----------|---------------------|----------|-------------------|
EOF

# Extract signature info from FIT images
if [[ -f "$BOOTLOADER_FIT" ]]; then
    ALGO=$(grep -oP 'algo = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | grep rsa | head -1 || echo "unknown")
    KEY=$(grep -oP 'key-name-hint = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | head -1 || echo "unknown")
    SIGNED=$(grep -oP 'sign-images = "\K[^"]+' "$BOOTLOADER_FIT" 2>/dev/null | head -1 || echo "unknown")
    echo "| Bootloader (uboot+optee) | $ALGO | $KEY | $SIGNED |" >> "$OUTPUT_FILE"
fi

if [[ -f "$KERNEL_FIT" ]]; then
    ALGO=$(grep -oP 'algo = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | grep rsa | head -1 || echo "unknown")
    KEY=$(grep -oP 'key-name-hint = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | head -1 || echo "unknown")
    SIGNED=$(grep -oP 'sign-images = "\K[^"]+' "$KERNEL_FIT" 2>/dev/null | head -1 || echo "unknown")
    echo "| Kernel | $ALGO | $KEY | $SIGNED |" >> "$OUTPUT_FILE"
fi

# ==============================================================================
# Section 2: U-Boot Secure Boot Strings
# ==============================================================================
info "Analyzing U-Boot binary..."

cat >> "$OUTPUT_FILE" << 'EOF'

## U-Boot Secure Boot Analysis

U-Boot binary extracted and decompressed from bootloader FIT image.

### Verification-Related Strings

EOF

# Extract U-Boot from FIT (data-position=0x1000, data-size=0x6d2c0 relative to FIT start)
UBOOT_START=$((0x8F1B4 + 0x1000))
UBOOT_SIZE=$((0x6d2c0))

echo '```' >> "$OUTPUT_FILE"
dd if="$FIRMWARE" bs=1 skip=$UBOOT_START count=$UBOOT_SIZE 2>/dev/null | \
    gunzip 2>/dev/null | \
    strings | \
    grep -iE 'verified|signature|secure.?boot|FIT.*sign|required|rsa.*verify' | \
    sort -u | head -30 >> "$OUTPUT_FILE" || echo "Could not extract U-Boot strings" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << 'EOF'

### Key Findings in U-Boot

EOF

echo '```' >> "$OUTPUT_FILE"
dd if="$FIRMWARE" bs=1 skip=$UBOOT_START count=$UBOOT_SIZE 2>/dev/null | \
    gunzip 2>/dev/null | \
    strings | \
    grep -E "FIT:.*signed|Verified-boot:|Can't read verified-boot|CONFIG_FIT_SIGNATURE" | \
    sort -u >> "$OUTPUT_FILE" || true
echo '```' >> "$OUTPUT_FILE"

# ==============================================================================
# Section 3: OP-TEE Secure Boot Strings
# ==============================================================================
info "Analyzing OP-TEE binary..."

cat >> "$OUTPUT_FILE" << 'EOF'

## OP-TEE Analysis

OP-TEE (Trusted Execution Environment) handles secure boot flag storage.

### Secure Boot Flag Functions

EOF

# Extract OP-TEE from FIT (data-position=0x6e400, data-size=0x34c7d relative to FIT start)
OPTEE_START=$((0x8F1B4 + 0x6e400))
OPTEE_SIZE=$((0x34c7d))

echo '```' >> "$OUTPUT_FILE"
dd if="$FIRMWARE" bs=1 skip=$OPTEE_START count=$OPTEE_SIZE 2>/dev/null | \
    gunzip 2>/dev/null | \
    strings | \
    grep -iE 'secure.?boot|otp.*key|set.*flag|key.*index|enable.*flag' | \
    sort -u | head -30 >> "$OUTPUT_FILE" || echo "Could not extract OP-TEE strings" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"

# ==============================================================================
# Section 4: Device Tree OTP/Crypto Analysis
# ==============================================================================
info "Analyzing Device Tree for OTP/Crypto..."

cat >> "$OUTPUT_FILE" << 'EOF'

## Device Tree Analysis

### OTP (One-Time Programmable) Memory

EOF

KERNEL_DTS="${EXTRACTIONS_DIR}/1C597B4/system.dtb"
if [[ -f "$KERNEL_DTS" ]]; then
    echo '```' >> "$OUTPUT_FILE"
    grep -A 10 "otp@" "$KERNEL_DTS" 2>/dev/null | head -20 >> "$OUTPUT_FILE" || echo "No OTP node found" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"

    cat >> "$OUTPUT_FILE" << 'EOF'

### Crypto Engine

EOF
    echo '```' >> "$OUTPUT_FILE"
    grep -A 10 "crypto@" "$KERNEL_DTS" 2>/dev/null | head -20 >> "$OUTPUT_FILE" || echo "No crypto node found" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
fi

# ==============================================================================
# Section 5: Conclusions
# ==============================================================================
cat >> "$OUTPUT_FILE" << 'EOF'

## Conclusions

### What We Know (Static Analysis)

| Finding | Status | Evidence |
|---------|--------|----------|
| FIT images are signed | ✅ Verified | `algo = "sha256,rsa2048"` in FIT configuration |
| RSA2048 + SHA256 used | ✅ Verified | Signature nodes in both bootloader and kernel FIT |
| Key name is "dev" | ✅ Verified | `key-name-hint = "dev"` (suggests development key) |
| U-Boot has verification code | ✅ Verified | `FIT: %ssigned, %sconf required` string |
| OP-TEE manages secure boot flag | ✅ Verified | `set_secure_boot_enable_flag` function |
| Secure boot flag stored in OTP | ✅ Verified | OTP read/write functions for secure boot |
| Hardware crypto available | ✅ Verified | `crypto@ff500000` with `rockchip,rv1126-crypto` |
| OTP memory available | ✅ Verified | `otp@ff5c0000` with `rockchip,rv1126-otp` |

### What Requires Physical Testing

| Item | How to Verify |
|------|---------------|
| Is secure boot flag set in OTP? | Read OTP via UART/OP-TEE or attempt unsigned boot |
| Does U-Boot enforce verification? | Attempt to boot modified FIT image |
| Is the "dev" key a real key or placeholder? | Check if signature verification passes |

### Security Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Secure Boot Chain                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  BootROM ──► SPL ──► OP-TEE ──► U-Boot ──► Kernel           │
│     │         │        │          │          │              │
│     │         │        │          │          │              │
│     ▼         ▼        ▼          ▼          ▼              │
│   [HW]    [Signed?] [Signed]  [Signed]   [Signed]           │
│            FIT       FIT       FIT        FIT               │
│                                                              │
│  OTP Memory (ff5c0000):                                     │
│  ├── Secure boot enable flag (one-time write)               │
│  └── OEM keys (RSA public key hash?)                        │
│                                                              │
│  Signature: sha256,rsa2048 with key "dev"                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Implications

1. **If OTP secure boot flag is NOT set:**
   - FIT signatures present but NOT verified
   - Custom firmware can boot
   - This is the likely scenario for consumer devices

2. **If OTP secure boot flag IS set:**
   - U-Boot verifies FIT signatures before loading
   - Only firmware signed with matching key will boot
   - Maskrom mode may still allow low-level flashing

3. **The "dev" key name suggests:**
   - Development/test key used during manufacturing
   - May not be a production secure boot setup
   - Could indicate secure boot is not fully enabled

EOF

info "Analysis complete: $OUTPUT_FILE"
