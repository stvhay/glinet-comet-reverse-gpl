# Boot Process and Partition Layout

[← Analysis Reports](SUMMARY.md)

---

The Comet uses a Rockchip RV1126 SoC with A/B partition redundancy for OTA updates. FIT images contain signed bootloader and kernel components.

## Hardware Platform

| Property | Value |
|----------|-------|
| SoC | Rockchip RV1126 |
| Architecture | ARM Cortex-A7 (32-bit) |
| Storage | eMMC |
| Device Tree | `rockchip,rv1126-evb-ddr3-v13` |

## Component Versions

| Component | Version | Source |
|-----------|---------|--------|
| U-Boot | 2017.09-gfd8bfa2acd-dirty | Binary strings |
| Linux Kernel | 4.19.111 | Module vermagic |
| Buildroot | 2018.02-rc3-gd56bbacb | /etc/os-release |
| OP-TEE | Present | FIT image |

## Boot Chain

See [Rockchip Boot Chain](../reference/rockchip-boot-chain.md) for the standard RV1126 boot sequence.

This firmware follows that sequence: BootROM → SPL → OP-TEE → U-Boot → Kernel → Initramfs → SquashFS rootfs.

## Partition Layout

| # | Name | Size | Type | Purpose |
|---|------|------|------|---------|
| 1 | uboot | ~2 MB | FIT | U-Boot + OP-TEE |
| 2 | reserved | ~2 MB | Raw | Rockchip parameters |
| 3 | dtb1 | ~12 MB | FIT | Kernel slot A |
| 4 | dtb2 | ~12 MB | FIT | Kernel slot B |
| 5 | misc | ~1 MB | Raw | Boot control block |
| 6 | rootfs | ~232 MB | SquashFS | Main filesystem (read-only) |
| 7 | oem | ~6 MB | EXT4 | Factory data |
| 8 | userdata | ~5 MB | EXT4 | User configuration |

## A/B Partition Scheme

The device uses A/B redundancy for safe OTA updates:

- **Slot A (dtb1)**: Recovery / fallback kernel
- **Slot B (dtb2)**: Normal boot kernel
- **Shared**: Both slots use the same U-Boot partition

Boot selection is controlled by the misc partition. On boot failure, U-Boot falls back to the other slot.

## FIT Image Structure

### Bootloader FIT (partition 1)

Contains U-Boot, OP-TEE, and device tree in a signed FIT image:

```
configurations/conf:
  firmware = "optee"
  loadables = "uboot"
  fdt = "fdt"
  signature: sha256,rsa2048, key="dev"
```

### Kernel FIT (partitions 3-4)

Contains kernel, device tree, and initramfs:

```
images:
  kernel (zImage)
  fdt (device tree)
  ramdisk (rootfs.cpio)
```

## Kernel Command Line

```
earlycon=uart8250,mmio32,0xff570000 console=ttyFIQ0 root=PARTUUID=614e0000-0000 rootfstype=squashfs rootwait
```

## Console Access

| Parameter | Value |
|-----------|-------|
| Console | ttyFIQ0 |
| Baud Rate | 1500000 |

## See Also

- [U-Boot Version](uboot-version.md) — Detailed bootloader analysis
- [Device Trees](device-trees.md) — Hardware configuration
- [Rockchip Secure Boot](../reference/rockchip-secure-boot.md) — Signature verification details
