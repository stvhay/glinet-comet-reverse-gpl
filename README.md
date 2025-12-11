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

## Who Must Provide Source Code?

GL.iNet must provide source code to any customer who requests it. This is their legal obligation under the GPL. They cannot point customers to Rockchip or other suppliers—each distributor has an independent obligation.

**[Read the full compliance analysis →](docs/GPL-COMPLIANCE-ANALYSIS.md)**

## Run Your Own Analysis

```bash
nix develop
./scripts/analyze.sh
```

Results go to `output/`. See the **[Wiki](https://github.com/stvhay/glinet-comet-reverse-gpl/wiki)** for detailed usage and analysis reports.

## Legal

This repository contains only scripts and documentation. No proprietary code or binaries are included.

## License

[GPL-2.0](LICENSE)
