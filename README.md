# GL.iNet Comet Copyleft License Compliance Analysis

[![CI](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml/badge.svg)](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml)

This project documents copyleft-licensed software in the GL.iNet Comet (GL-RM1) KVM firmware and tracks compliance with source code disclosure requirements.

## Compliance Status Summary

> **[Full Compliance Analysis](docs/GPL-COMPLIANCE-ANALYSIS.md)** - Detailed legal analysis with source code request template

| Component | Version | License | Source Available? |
|-----------|---------|---------|:-----------------:|
| Linux Kernel | 4.19.111 | GPL-2.0 | :x: No |
| U-Boot | 2017.09 | GPL-2.0+ | :x: No |
| BusyBox | 1.27.2 | GPL-2.0 | :x: No |
| GNU Coreutils | - | GPL-3.0+ | :x: No |
| bcmdhd WiFi Driver | - | GPL-2.0 | :x: No |
| FFmpeg | 58.x | LGPL-2.1+ | :x: No |
| BlueZ | 3.18.16 | GPL-2.0+ | :x: No |
| Janus Gateway | 2.0.6 | GPL-3.0 | :x: No |
| glibc | 2.28 | LGPL-2.1+ | :x: No |
| Buildroot Config | 2018.02-rc3 | GPL-2.0+ | :x: No |
| KVMD (Application) | - | GPL-3.0 | :white_check_mark: [Yes](https://github.com/gl-inet/glkvm) |

**Legend:** :white_check_mark: Source code publicly available | :x: Source code NOT available

### Who Must Provide Source Code?

**GL.iNet is responsible for providing source code to customers.** Under GPL, each entity in the distribution chain has an independent compliance obligation. As the distributor to end users, GL.iNet cannot delegate this to Rockchip or other upstream vendors - they must provide source code themselves upon request.

As of December 2025, only the application-layer KVMD code has been released. The kernel, bootloader, drivers, and build system configuration have not been made available despite [user requests on the GL.iNet forum](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955).

## Purpose

GL.iNet distributes firmware containing copyleft-licensed software. This project:

1. Downloads the publicly available firmware
2. Extracts and identifies copyleft-licensed components
3. Documents source code disclosure obligations
4. Tracks compliance status

## Quick Start

### Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled
- Or [direnv](https://direnv.net/) for automatic environment loading

### Run Analysis

```bash
# Enter the development environment
nix develop

# Run the analysis script
./scripts/analyze.sh
```

Output files are written to `output/` as markdown.

### With direnv

```bash
direnv allow
./scripts/analyze.sh
```

### Extract Partitions from Device

If you have physical access to a GL.iNet Comet device, you can extract the raw eMMC partitions:

1. Copy the config template:
   ```bash
   cp config.env.template config.env
   ```

2. Edit `config.env` with your device's IP and root password (same as web interface password)

3. Connect to your device's network and run:
   ```bash
   ./scripts/extract-partitions.sh
   ```

This performs **read-only** operations on the device - no data is written. Partitions are saved to `partitions/`.

## Documentation

### Compliance Analysis

| Document | Description |
|----------|-------------|
| **[Full Compliance Analysis](docs/GPL-COMPLIANCE-ANALYSIS.md)** | Legal analysis, component list, source code request template |

### Technical Analysis

| Report | Description |
|--------|-------------|
| [Summary](docs/analysis/SUMMARY.md) | Overview of firmware analysis |
| [Kernel Version](docs/analysis/kernel-version.md) | Linux kernel 4.19.111 |
| [U-Boot Version](docs/analysis/uboot-version.md) | U-Boot 2017.09 |
| [Device Trees](docs/analysis/device-trees.md) | DTB/FIT image analysis |
| [GPL Binaries](docs/analysis/gpl-binaries.md) | BusyBox, coreutils, etc. |
| [Kernel Modules](docs/analysis/kernel-modules.md) | Loadable kernel modules |
| [Build Info](docs/analysis/build-info.md) | Buildroot 2018.02-rc3 |
| [License Files](docs/analysis/license-files.md) | License files in firmware |
| [Shared Libraries](docs/analysis/packages.md) | LGPL/GPL libraries |

To regenerate locally: `./scripts/analyze.sh && cp output/*.md docs/analysis/`

**For forks:** CI automatically generates fresh analysis on every push - check the Actions tab for artifacts, or tag a release to get reports attached automatically.

## Directory Structure

| Directory | Contents | Committed |
|-----------|----------|-----------|
| `scripts/` | Analysis scripts | Yes |
| `docs/analysis/` | Analysis reports | Yes |
| `docs/rockchip-sdk/` | SDK documentation (submodule) | Yes |
| `downloads/` | Cached firmware `.img` | No |
| `output/` | Local analysis output | No |
| `partitions/` | Raw eMMC partition dumps | No |

### Firmware vs Partitions

- **`downloads/*.img`** - Rockchip update image from GL.iNet (publicly available, ~261MB compressed)
- **`partitions/*.bin`** - Raw eMMC partition dumps from physical device (~7.3GB total)

The `.img` is a compressed update package containing the essential system partitions. The raw partition dumps include additional data (userdata, oem, media) not present in the update image. CI analyzes the public `.img`; partition dumps are for local deep analysis.

## Related Resources

- [GL.iNet Forum: Comet GL-RM1 and open source](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955) - Community discussion on source code availability
- [GL.iNet GLKVM Repository](https://github.com/gl-inet/glkvm) - Application-layer source (KVMD)
- [Rockchip Open Source](https://opensource.rock-chips.com/) - Rockchip SDK documentation
- [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) - License text
- [GNU LGPL v2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html) - License text

## Legal

This repository contains only:

- Scripts to download publicly available firmware
- Analysis tools and documentation
- No proprietary code or binary files

The analysis is provided for informational purposes to document GPL compliance obligations.

## License

This project is licensed under the [GNU General Public License v2.0](LICENSE) (GPL-2.0).
