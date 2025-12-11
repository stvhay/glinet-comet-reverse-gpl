# Boot Process and Partition Layout

**GL.iNet Comet (GL-RM1) Firmware**

Generated: 2025-12-11

## Executive Summary

The GL.iNet Comet uses a Rockchip RV1126 SoC with a standard Rockchip boot chain. The device employs an A/B partition scheme for redundancy, with FIT (Flattened Image Tree) images containing the bootloader, TEE, kernel, and device trees.

## Hardware Platform

| Property | Value |
|----------|-------|
| **SoC** | Rockchip RV1126 |
| **Architecture** | ARM Cortex-A7 (32-bit ARMv7) |
| **Storage** | eMMC |
| **Device Tree Compatible** | `rockchip,rv1126-evb-ddr3-v13` |

## Boot Chain

```
┌─────────────┐
│  Power On   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  BootROM    │  Rockchip mask ROM (fixed in silicon)
│  (BROM)     │  - Initializes basic hardware
└──────┬──────┘  - Loads SPL from eMMC/SD
       │
       ▼
┌─────────────┐
│  SPL/TPL    │  Secondary Program Loader
│             │  - DDR memory initialization
└──────┬──────┘  - Loads U-Boot FIT image
       │
       ▼
┌─────────────┐
│  OP-TEE     │  Trusted Execution Environment
│  (tee.bin)  │  - Secure world initialization
└──────┬──────┘  - Size: ~216 KB (compressed)
       │
       ▼
┌─────────────┐
│  U-Boot     │  Version: 2017.09-gfd8bfa2acd-dirty
│             │  - Hardware initialization
└──────┬──────┘  - Loads kernel FIT image
       │         - Size: ~447 KB (compressed)
       ▼
┌─────────────┐
│  Linux      │  Version: 4.19.111
│  Kernel     │  - ARM 32-bit, SMP, preempt
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Initramfs  │  rootfs.cpio (~8.3 MB)
│             │  - Early userspace init
└──────┬──────┘  - Mounts SquashFS root
       │
       ▼
┌─────────────┐
│  SquashFS   │  Main root filesystem
│  Rootfs     │  - Size: ~231 MB
└─────────────┘  - Read-only, gzip compressed
```

## Partition Layout

### eMMC Partition Table

| Partition | Device | Name | Size | Filesystem | Purpose |
|-----------|--------|------|------|------------|---------|
| 1 | mmcblk0p1 | uboot | ~2 MB | FIT Image | U-Boot + OP-TEE FIT image |
| 2 | mmcblk0p2 | reserved | ~2 MB | Raw | Rockchip reserved (misc/param) |
| 3 | mmcblk0p3 | dtb1 | ~12 MB | FIT Image | Kernel FIT (slot A / recovery) |
| 4 | mmcblk0p4 | dtb2 | ~12 MB | FIT Image | Kernel FIT (slot B / normal) |
| 5 | mmcblk0p5 | misc | ~1 MB | Raw | Boot control / recovery flags |
| 6 | mmcblk0p6 | rootfs | ~232 MB | SquashFS | Main root filesystem (read-only) |
| 7 | mmcblk0p7 | oem | ~6 MB | EXT4 | OEM data / factory settings |
| 8 | mmcblk0p8 | userdata | ~5 MB | EXT4 | User configuration data |
| 9 | mmcblk0p9 | config | Variable | Unknown | Additional configuration |
| 10 | mmcblk0p10 | extended | Variable | Unknown | Extended partition container |

### Partition Purposes

#### Boot Partitions (1-5)

- **uboot (p1)**: Contains the bootloader FIT image with:
  - U-Boot binary (u-boot-nodtb.bin)
  - OP-TEE binary (tee.bin)
  - U-Boot device tree

- **reserved (p2)**: Rockchip parameter partition
  - May contain boot parameters
  - Recovery mode flags

- **dtb1/dtb2 (p3/p4)**: Kernel FIT images containing:
  - Linux kernel (zImage)
  - Kernel device tree (DTB)
  - Initramfs (rootfs.cpio)
  - Likely A/B slot redundancy

- **misc (p5)**: Boot control block
  - A/B slot selection
  - Recovery mode trigger
  - OTA update status

#### System Partitions (6-7)

- **rootfs (p6)**: Main operating system
  - SquashFS compressed filesystem
  - Read-only for integrity
  - Contains Buildroot 2018.02-rc3 system
  - BusyBox, KVMD, system services

- **oem (p7)**: OEM/Factory data
  - Device-specific calibration
  - Factory test results
  - MAC addresses, serial numbers

#### Data Partitions (8-10)

- **userdata (p8)**: Persistent user data
  - User configuration
  - Survives factory reset
  - EXT4 filesystem

- **config (p9)**: Additional configuration
  - May overlap with userdata purpose

## FIT Image Structure

### Bootloader FIT (mmcblk0p1)

```
FIT Image: "FIT Image with ATF/OP-TEE/U-Boot/MCU"
├── images/
│   ├── uboot
│   │   ├── description = "U-Boot"
│   │   ├── type = "standalone"
│   │   ├── arch = "arm"
│   │   ├── os = "U-Boot"
│   │   └── compression = "gzip"
│   ├── optee
│   │   ├── description = "OP-TEE"
│   │   ├── type = "firmware"
│   │   ├── arch = "arm"
│   │   ├── os = "op-tee"
│   │   └── compression = "gzip"
│   └── fdt
│       ├── description = "U-Boot dtb"
│       ├── type = "flat_dt"
│       └── compression = "none"
└── configurations/
    └── rv1126-evb
```

### Kernel FIT (mmcblk0p3/p4)

```
FIT Image: "U-Boot FIT source file for arm"
├── images/
│   ├── fdt
│   │   ├── type = "flat_dt"
│   │   ├── arch = "arm"
│   │   └── compression = "none"
│   ├── kernel
│   │   ├── type = "kernel"
│   │   ├── arch = "arm"
│   │   ├── os = "linux"
│   │   └── compression = "none"
│   └── ramdisk
│       ├── type = "ramdisk"
│       ├── arch = "arm"
│       ├── os = "linux"
│       └── compression = "none"
└── configurations/
    └── default
```

## A/B Partition Scheme

The device appears to use an A/B partition scheme for OTA updates:

| Slot | Bootloader | Kernel | Purpose |
|------|------------|--------|---------|
| A | uboot (p1) | dtb1 (p3) | Recovery / Fallback |
| B | uboot (p1) | dtb2 (p4) | Normal boot |

**Note:** Both kernel slots share the same U-Boot partition. The bootloader FIT image appears duplicated within the firmware image (at offsets 0x8F1B4 and 0x28F1B4) suggesting redundancy.

### Boot Selection Logic

1. U-Boot reads boot control block from misc partition
2. Selects active slot (A or B)
3. Loads kernel FIT from corresponding dtb partition
4. Falls back to other slot on boot failure

## OTA Update Mechanism

Based on the A/B partition scheme:

1. **Download**: New firmware downloaded to inactive slot
2. **Verify**: Checksum/signature verification
3. **Mark**: Update boot control to switch slots
4. **Reboot**: Boot into new firmware
5. **Rollback**: If boot fails, revert to previous slot

## Security Features

### OP-TEE (Trusted Execution Environment)

- Secure world for sensitive operations
- Key storage and cryptographic operations
- May handle secure boot verification

### Potential Secure Boot

The presence of:
- SHA256 hash constants in firmware
- OP-TEE integration
- FIT image signatures (possible)

Suggests secure boot may be enabled, though verification status is unknown without runtime analysis.

## Kernel Command Line

Typical Rockchip kernel parameters (requires runtime verification):

```
console=ttyFIQ0 root=/dev/mmcblk0p6 rootfstype=squashfs ro
```

## Mount Points (Runtime)

Expected mount configuration:

| Mount Point | Device | Filesystem | Options |
|-------------|--------|------------|---------|
| `/` | mmcblk0p6 | squashfs | ro |
| `/oem` | mmcblk0p7 | ext4 | rw |
| `/userdata` | mmcblk0p8 | ext4 | rw |

## Version Information

| Component | Version | Source |
|-----------|---------|--------|
| U-Boot | 2017.09-gfd8bfa2acd-dirty | Binary strings |
| Linux Kernel | 4.19.111 | Module vermagic |
| Buildroot | 2018.02-rc3-gd56bbacb | /etc/os-release |
| Build Date | 2025-11-27/28 | Firmware timestamps |

## References

- [Rockchip Boot Flow](https://opensource.rock-chips.com/wiki_Boot_option)
- [U-Boot FIT Images](https://u-boot.readthedocs.io/en/latest/usage/fit/index.html)
- [Device Trees Analysis](device-trees.md)
- [U-Boot Version](uboot-version.md)
- [Build Information](build-info.md)

## Tasks Completed

- [x] Document boot chain stages
- [x] Map partition layout
- [x] Analyze FIT image structure
- [x] Identify A/B slot scheme
- [x] Document component versions

## Tasks Remaining

- [ ] Verify partition purposes with runtime analysis
- [ ] Extract U-Boot environment variables
- [ ] Confirm kernel command line
- [ ] Test A/B slot switching
- [ ] Verify secure boot status
