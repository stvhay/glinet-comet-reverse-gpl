# Usage Guide

How to run the analysis tools in this repository.

## Quick Start

You need [Nix](https://nixos.org/download.html) with flakes enabled.

```bash
nix develop
./scripts/analyze.sh
```

Results go to `output/`. The script downloads the firmware automatically.

## Analyze a Different Firmware Version

```bash
./scripts/analyze.sh https://example.com/other-firmware.img
```

## Extract from a Physical Device

If you own a Comet, you can dump the partitions directly:

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
