# Firmware Analysis Reports

[← Back to README](../../README.md) · [GPL Compliance Analysis →](../GPL-COMPLIANCE-ANALYSIS.md)

---

These reports document what we found by extracting and analyzing the GL.iNet Comet firmware.

**Firmware:** glkvm-RM1-1.7.2-1128-1764344791.img
**Platform:** Rockchip RV1126, Linux 4.19.111, Buildroot 2018.02-rc3

## Key Components

| Component | Version | License | Details |
|-----------|---------|---------|---------|
| Linux Kernel | 4.19.111 | GPL-2.0 | [kernel-version.md](kernel-version.md) |
| U-Boot | 2017.09 | GPL-2.0+ | [uboot-version.md](uboot-version.md) |
| BusyBox | 1.27.2 | GPL-2.0 | [gpl-binaries.md](gpl-binaries.md) |

## License Analysis

- [Automated License Detection](licenses.md) — Licenses identified in binaries and metadata
- [GPL Binaries](gpl-binaries.md) — BusyBox, coreutils, and other GPL-licensed tools
- [License Files](license-files.md) — License and copyright files found in filesystem

## System Components

- [Kernel Version](kernel-version.md) — Linux kernel version from module vermagic
- [Kernel Modules](kernel-modules.md) — Loadable kernel modules (.ko files)
- [U-Boot Version](uboot-version.md) — Bootloader version and build info
- [Shared Libraries](packages.md) — System libraries (.so files)
- [Build Info](build-info.md) — OS release and build configuration

## Device Internals

- [Boot Process](boot-process.md) — Boot chain, partitions, FIT images
- [Device Trees](device-trees.md) — Hardware configuration from DTBs
- [Network Services](network-services.md) — Running services and attack surface
- [Proprietary Blobs](proprietary-blobs.md) — Rockchip closed-source libraries
- [Flashing Methods](flashing-methods.md) — How to flash custom firmware

## Firmware Structure

- [Binwalk Scan](binwalk-scan.md) — Firmware layout and embedded files

## Reference Documentation

Background information (not specific to this firmware):

- [Rockchip Boot Chain](../reference/rockchip-boot-chain.md)
- [Rockchip Secure Boot](../reference/rockchip-secure-boot.md)
- [Rockchip License Info](../reference/rockchip-license-info.md)
- [GPL Compliance Requirements](../reference/gpl-compliance.md)
