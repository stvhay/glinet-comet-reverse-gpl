# GL.iNet Comet GPL Compliance Analysis

[![CI](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml/badge.svg)](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml)

**GL.iNet ships GPL-licensed software in their Comet KVM device but has not released the required source code.**

This project analyzes the firmware to document what source code GL.iNet must provide under the GPL license.

## Key Findings

The Comet (GL-RM1) contains at least 10 GPL-licensed components. GL.iNet has released source code for only one of them.

| Component | License | Source Released? |
|-----------|---------|:----------------:|
| Linux Kernel 4.19.111 | GPL-2.0 | :x: No |
| U-Boot 2017.09 | GPL-2.0+ | :x: No |
| BusyBox 1.27.2 | GPL-2.0 | :x: No |
| GNU Coreutils | GPL-3.0+ | :x: No |
| bcmdhd WiFi Driver | GPL-2.0 | :x: No |
| FFmpeg 58.x | LGPL-2.1+ | :x: No |
| BlueZ 3.18.16 | GPL-2.0+ | :x: No |
| Janus Gateway 2.0.6 | GPL-3.0 | :x: No |
| glibc 2.28 | LGPL-2.1+ | :x: No |
| Buildroot 2018.02-rc3 | GPL-2.0+ | :x: No |
| KVMD Application | GPL-3.0 | :white_check_mark: [Yes](https://github.com/gl-inet/glkvm) |

Users have [requested source code on the GL.iNet forum](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955). As of December 2025, GL.iNet has not provided it.

**[Read the full compliance analysis →](docs/GPL-COMPLIANCE-ANALYSIS.md)**

## Who Must Provide Source Code?

GL.iNet must provide source code to any customer who requests it. This is their legal obligation under the GPL.

GL.iNet cannot point customers to Rockchip or other suppliers. Each company that distributes GPL software has an independent obligation to provide source code.

## Analysis Reports

We extracted the firmware and documented what we found.

### License Analysis
- [Automated License Detection](docs/analysis/licenses.md) — Which components have which licenses
- [GPL Binaries](docs/analysis/gpl-binaries.md) — BusyBox, coreutils, and other GPL tools
- [License Files](docs/analysis/license-files.md) — License files included in firmware

### System Components
- [Kernel Version](docs/analysis/kernel-version.md) — Linux 4.19.111
- [U-Boot Version](docs/analysis/uboot-version.md) — U-Boot 2017.09
- [Kernel Modules](docs/analysis/kernel-modules.md) — Loadable kernel modules
- [Shared Libraries](docs/analysis/packages.md) — System libraries

### Device Internals
- [Boot Process](docs/analysis/boot-process.md) — How the device boots, partition layout
- [Device Trees](docs/analysis/device-trees.md) — Hardware configuration
- [Network Services](docs/analysis/network-services.md) — Running services and security
- [Proprietary Blobs](docs/analysis/proprietary-blobs.md) — Closed-source Rockchip libraries
- [Flashing Methods](docs/analysis/flashing-methods.md) — How to flash custom firmware

## Run Your Own Analysis

You need [Nix](https://nixos.org/download.html) with flakes enabled.

```bash
nix develop
./scripts/analyze.sh
```

Results go to `output/`. The script downloads the firmware automatically.

### Analyze a Different Firmware Version

```bash
./scripts/analyze.sh https://example.com/other-firmware.img
```

### Extract from a Physical Device

If you own a Comet, you can dump the partitions:

```bash
cp config.env.template config.env
# Edit config.env with device IP and password
./scripts/extract-partitions.sh
```

This only reads data. Nothing is written to the device.

## Project Structure

| Directory | Contents |
|-----------|----------|
| `scripts/` | Analysis scripts |
| `docs/analysis/` | Generated reports |
| `docs/GPL-COMPLIANCE-ANALYSIS.md` | Legal analysis |
| `downloads/` | Cached firmware (not committed) |
| `output/` | Local analysis output (not committed) |

## Resources

- [GL.iNet Forum Discussion](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955)
- [GL.iNet KVMD Source](https://github.com/gl-inet/glkvm) (application layer only)
- [Rockchip Open Source](https://opensource.rock-chips.com/)
- [GPL v2 License Text](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

## Legal

This repository contains only scripts and documentation. No proprietary code or binaries are included. The analysis documents GPL compliance obligations for informational purposes.

## License

[GPL-2.0](LICENSE)
