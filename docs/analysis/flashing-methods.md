# Flashing Methods and Hardware Requirements

**GL.iNet Comet (GL-RM1)**

Generated: 2025-12-11

## Overview

This document describes potential methods for flashing custom firmware to the GL.iNet Comet device. The device is based on the Rockchip RV1126 SoC, which supports several standard Rockchip flashing mechanisms.

> **Status:** Research-based documentation. Methods marked with ⚠️ require physical device verification. Signature verification conclusions are based on static binary analysis and have not been tested on a physical device.

## Device Platform

| Property | Value |
|----------|-------|
| SoC | Rockchip RV1126 |
| Architecture | ARM Cortex-A7 (32-bit) |
| Storage | eMMC |
| USB | Likely USB 2.0 OTG |

## Flashing Methods

### 1. OTA Update (Software Only)

**Difficulty:** Easy (if format is compatible)
**Hardware Required:** None (network access only)

The device supports over-the-air updates through the KVMD web interface.

#### Update Package Format

Based on binwalk analysis of `glkvm-RM1-1.7.2-*.img`:

```
Offset      Size        Content
────────────────────────────────────────────────
0x000000    ~586KB      Header / Rockchip image header
0x08F1B4    ~2KB        U-Boot DTB
0x0901B4    ~447KB      U-Boot (gzip compressed)
0x0FD5B4    ~216KB      OP-TEE (gzip compressed)
0x1323B4    ~11KB       U-Boot DTB (full)
0x28F1B4    ...         [Duplicate bootloader - slot B]
0x49B1B4    ~1.5KB      Kernel FIT header
0x49B9B4    ~97KB       Kernel DTB
0x1465DB4   ~8.3MB      Initramfs (rootfs.cpio, gzip)
0x1C597B4   ~97KB       Kernel DTB
0x1CEA1B4   ~231MB      SquashFS root filesystem
0xF9E01B4   ~6MB        EXT4 (oem partition)
0xFFE01B4   ~5MB        EXT4 (userdata partition)
```

#### Creating Custom Update

✅ **Verified:** Updates do NOT require cryptographic signatures.

Analysis of the firmware validation binaries (`check_image_validity` and `updateEngine`) shows:
- Only MD5 checksums and CRC32 are used for integrity verification
- String `"md5 : not support sign image."` explicitly indicates no signature support
- Model string verification ensures firmware matches device (GL-RM1)
- No RSA, ECDSA, or other cryptographic signature functions present

This means custom firmware can be flashed if:
1. The image passes MD5/CRC32 integrity checks
2. The model string matches the target device

To create a custom update package:
1. Modify the SquashFS rootfs
2. Repack in Rockchip update format (preserving headers and checksums)
3. Upload via web interface or `scp` to device

**Tools needed:**
- `mksquashfs` - Create SquashFS images
- Rockchip `afptool` / `rkImageMaker` - Pack update image
- MD5 checksum tools - Update integrity checksums

### 2. USB Maskrom Mode ⚠️

**Difficulty:** Moderate
**Hardware Required:** USB cable, possibly test point access

Rockchip SoCs have a built-in "Maskrom" mode that allows low-level flashing via USB when normal boot fails.

#### Entering Maskrom Mode

Standard methods for RV1126:

1. **Button method:** Hold recovery button while powering on
2. **Test point method:** Short specific eMMC pins during boot
3. **Software method:** Corrupt bootloader to force maskrom
4. **U-Boot command:** `rockusb 0 mmc 0` (if U-Boot accessible)

⚠️ **Needs verification:** Which method works on GL-RM1

#### USB IDs (Expected)

| Mode | VID:PID |
|------|---------|
| Maskrom | 2207:110b (RV1126) |
| Loader | 2207:110b |

#### Flashing via Maskrom

```bash
# Install rkdeveloptool
git clone https://github.com/rockchip-linux/rkdeveloptool
cd rkdeveloptool && autoreconf -i && ./configure && make

# Check device connection
sudo rkdeveloptool ld

# Flash loader (needed first in maskrom)
sudo rkdeveloptool db rv1126_loader.bin

# Flash full update image
sudo rkdeveloptool uf update.img

# Or flash individual partitions
sudo rkdeveloptool wl 0x0 uboot.img        # Write to offset 0
sudo rkdeveloptool wl 0x8000 boot.img      # Write boot partition
```

### 3. SD Card Boot ⚠️

**Difficulty:** Easy (if supported)
**Hardware Required:** MicroSD card

Some RV1126 boards support booting from SD card, which can be used for recovery.

#### SD Card Image Format

```bash
# Create bootable SD card (theoretical)
dd if=sdcard-update.img of=/dev/sdX bs=4M
```

⚠️ **Needs verification:** Whether GL-RM1 has SD card slot or supports SD boot

### 4. UART Console Access ⚠️

**Difficulty:** Moderate
**Hardware Required:** USB-UART adapter, possibly soldering

UART provides console access for debugging and may allow interrupting boot.

#### UART Settings (Verified from DTS)

| Parameter | Value | Source |
|-----------|-------|--------|
| Baud Rate | 1500000 | ✅ DTS: `rockchip,baudrate = <0x16e360>` |
| Data Bits | 8 | Standard |
| Parity | None | Standard |
| Stop Bits | 1 | Standard |
| Flow Control | None | Standard |
| Console Device | ttyFIQ0 | ✅ DTS: `console=ttyFIQ0` |
| UART Address | 0xff570000 | ✅ DTS: serial2, fiq-debugger |

#### Finding UART Pins

Look for:
- 3-4 pin header labeled "DEBUG" or "UART"
- Test points near SoC labeled TX, RX, GND
- Unpopulated header footprint

⚠️ **Needs verification:** UART pin locations on GL-RM1 PCB

#### Using UART for Flashing

```bash
# Connect via screen/minicom
screen /dev/ttyUSB0 1500000

# Interrupt U-Boot (press key during countdown)
# Then use U-Boot commands:
=> rockusb 0 mmc 0     # Enter USB download mode
=> ums 0 mmc 0         # USB Mass Storage mode
```

### 5. Direct eMMC Access ⚠️

**Difficulty:** Hard
**Hardware Required:** eMMC reader, possibly desoldering

Last resort method - directly read/write eMMC chip.

#### Methods

1. **eMMC socket adapter** - If eMMC is socketed (unlikely)
2. **ISP clip** - In-system programming if test points available
3. **Desoldering** - Remove eMMC, use adapter to flash, resolder

**Not recommended** unless device is already bricked.

## Required Tools

### Software

| Tool | Purpose | Source |
|------|---------|--------|
| `rkdeveloptool` | Linux flashing tool | [GitHub](https://github.com/rockchip-linux/rkdeveloptool) |
| `upgrade_tool` | Official Rockchip tool (Linux) | Rockchip SDK |
| `RKDevTool` | Official Windows GUI | Rockchip SDK |
| `rkbin` | Loader binaries | [GitHub](https://github.com/rockchip-linux/rkbin) |

### Loader Files Needed

For maskrom flashing, you need:
- `rv1126_ddr_924MHz_v*.bin` - DDR initialization
- `rv1126_usbplug_v*.bin` - USB download plugin
- `rv1126_loader_v*.bin` - Combined loader

These can be found in:
- Rockchip SDK
- [rkbin repository](https://github.com/rockchip-linux/rkbin)

## Firmware Image Formats

### Rockchip Update Image (.img)

The GL.iNet firmware uses Rockchip's update image format:

```
┌─────────────────────────────────────┐
│ RKAF Header (Rockchip Android FW)   │
├─────────────────────────────────────┤
│ Partition 1: uboot (FIT)            │
├─────────────────────────────────────┤
│ Partition 2: trust (OP-TEE)         │
├─────────────────────────────────────┤
│ Partition 3: boot (Kernel FIT)      │
├─────────────────────────────────────┤
│ Partition 4: rootfs (SquashFS)      │
├─────────────────────────────────────┤
│ Partition 5: oem (EXT4)             │
├─────────────────────────────────────┤
│ Partition 6: userdata (EXT4)        │
└─────────────────────────────────────┘
```

### Parameter File

Rockchip images include a parameter file defining partition layout:

```
# Example parameter format (needs extraction/verification)
FIRMWARE_VER:1.0
MACHINE_MODEL:GL-RM1
MACHINE_ID:007
MANUFACTURER:GL.iNet
MAGIC:0x5041524B
ATAG:0x00200800
MACHINE:rv1126
CHECK_MASK:0x80
PWR_HLD:0,0,A,0,1
TYPE:GPT
CMDLINE:mtdparts=rk29xxnand:0x2000@0x2000(uboot),...
```

## Security Considerations

### Firmware Signature Verification ✅

**Verified: NO cryptographic signatures required.**

Analysis of firmware validation binaries from the rootfs:

| Binary | Purpose | Verification Method |
|--------|---------|---------------------|
| `/usr/sbin/check_image_validity` | Pre-upgrade validation | MD5 checksum, model string |
| `/usr/bin/updateEngine` | Performs upgrade | MD5 checksum, CRC32 |

Key strings found in `check_image_validity`:
```
md5 : not support sign image.
Invalid: The device model is %s, but the image only supports %s
```

Key strings found in `updateEngine`:
```
MD5Check is error of %s
MD5Check is ok of %s
calculate crc32: %x.
```

**Implications:**
- Custom firmware CAN be installed via OTA mechanism
- Only requirements: correct MD5/CRC32 checksums and model string
- No RSA/ECDSA signature verification to bypass
- Bootloader modification may still require maskrom (separate from OTA)

### Secure Boot (Bootloader Level) ⚠️

**Unknown status** at the bootloader level. The bootloader may still have:
- Signed bootloader verification (separate from OTA)
- eFuse-burned keys for early boot stages

This affects:
- Custom U-Boot installation (may be rejected)
- Early boot chain modifications

Does NOT affect:
- Rootfs modifications via OTA (verified: no signatures)
- Application-level changes

### OP-TEE

The device includes OP-TEE (Trusted Execution Environment):
- Secure key storage
- Handles secure world operations
- Cannot be easily modified

## Recommendations

### For Initial Testing

1. **Try OTA first** - Least risk, no hardware needed
   - Extract rootfs from .img
   - Modify and repack with correct checksums
   - ✅ Device accepts unsigned updates (verified via binary analysis)

2. **Check for recovery mode** - Look for button combinations
   - Hold reset while powering on
   - Try different button timings

3. **Get UART access** - Most valuable for debugging
   - Identify UART pins on PCB
   - Connect and capture boot log
   - Try interrupting U-Boot

### For Development

1. Set up rkdeveloptool environment
2. Obtain RV1126 loader files from rkbin
3. Create backup of all partitions first
4. Test with non-critical partitions (oem, userdata)

## Verified Information

| Item | Status | Notes |
|------|--------|-------|
| SoC is RV1126 | ✅ Verified | From device tree |
| Uses Rockchip update format | ✅ Verified | Binwalk analysis |
| A/B partition scheme | ✅ Verified | Firmware structure |
| U-Boot 2017.09 | ✅ Verified | Binary strings |
| OP-TEE present | ✅ Verified | tee.bin in image |
| OTA accepts unsigned firmware | ✅ Verified | Binary strings analysis |
| Uses MD5/CRC32 checksums | ✅ Verified | Binary strings analysis |
| UART baud rate 1500000 | ✅ Verified | Device tree (fiq-debugger) |
| Console is ttyFIQ0 | ✅ Verified | Device tree (chosen/bootargs) |

## Needs Verification

| Item | Method to Verify |
|------|------------------|
| Maskrom mode entry | Physical device testing |
| UART pin locations | PCB inspection |
| Bootloader secure boot | Attempt custom U-Boot flash |
| SD card boot support | Check for SD slot |
| Recovery button | Physical inspection |
| USB maskrom VID:PID | Connect in maskrom mode |

## References

- [Rockchip Boot Option Wiki](https://opensource.rock-chips.com/wiki_Boot_option)
- [Rockchip Partitions Wiki](https://opensource.rock-chips.com/wiki_Partitions)
- [rkdeveloptool GitHub](https://github.com/rockchip-linux/rkdeveloptool)
- [rkbin (loader binaries)](https://github.com/rockchip-linux/rkbin)
- [Boot Process Documentation](boot-process.md)
- [Binwalk Analysis](binwalk-scan.md)
- [GL.iNet KVMD Source](https://github.com/gl-inet/glkvm) - upgrade.py shows validation flow
