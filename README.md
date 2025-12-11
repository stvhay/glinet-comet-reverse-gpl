# GL.iNet Comet GPL Compliance Analysis

[![CI](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml/badge.svg)](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml)

This project provides tools to analyze the GL.iNet Comet (RM1) KVM firmware and document GPL-licensed components for compliance purposes.

## Purpose

GL.iNet distributes firmware containing GPL-licensed software. This project:

1. Downloads the publicly available firmware
2. Extracts and analyzes its contents
3. Documents GPL-licensed components that require source code disclosure

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

## Analysis Results

See the [Analysis Summary](docs/analysis/SUMMARY.md) for the full GPL compliance report.

| Report | Description |
|--------|-------------|
| [Summary](docs/analysis/SUMMARY.md) | Overview of findings |
| [Kernel Version](docs/analysis/kernel-version.md) | Linux kernel 4.19.111 |
| [U-Boot Version](docs/analysis/uboot-version.md) | U-Boot 2017.09 |
| [Device Trees](docs/analysis/device-trees.md) | DTB/FIT image analysis |
| [GPL Binaries](docs/analysis/gpl-binaries.md) | BusyBox, coreutils, etc. |
| [Kernel Modules](docs/analysis/kernel-modules.md) | Loadable kernel modules |
| [Build Info](docs/analysis/build-info.md) | Buildroot 2018.02-rc3 |
| [License Files](docs/analysis/license-files.md) | License files in firmware |

To regenerate locally, run `./scripts/analyze.sh` and copy output to `docs/analysis/`.

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

## Legal

This repository contains only:

- Scripts to download publicly available firmware
- Analysis tools
- Documentation

No proprietary code or binary files are committed to this repository.

## License

MIT
