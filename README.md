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

## Output

The analysis produces markdown files documenting:

- **SUMMARY.md** - Overview of findings
- **build-info.md** - OS and build system information
- **gpl-binaries.md** - GPL-licensed binaries (BusyBox, coreutils, etc.)
- **kernel-modules.md** - Linux kernel modules
- **license-files.md** - License files found in firmware

See [Releases](https://github.com/stvhay/glinet-comet-reverse-gpl/releases) for pre-generated analysis results.

## Directory Structure

| Directory | Contents | Committed |
|-----------|----------|-----------|
| `scripts/` | Analysis scripts | Yes |
| `docs/` | SDK documentation (submodule) | Yes |
| `downloads/` | Cached firmware `.img` | No |
| `output/` | Generated analysis results | No |
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
