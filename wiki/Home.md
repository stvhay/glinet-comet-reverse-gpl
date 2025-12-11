# GL.iNet Comet GPL Compliance Analysis

**GL.iNet ships GPL-licensed software in their Comet KVM device but has not released the required source code.**

This wiki documents what source code GL.iNet must provide under the GPL license.

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

## Quick Links

- **[Full GPL Compliance Analysis](GPL-COMPLIANCE-ANALYSIS)** — Detailed legal analysis
- **[Analysis Summary](SUMMARY)** — Index of all technical analysis reports

## Who Must Provide Source Code?

GL.iNet must provide source code to any customer who requests it. This is their legal obligation under the GPL.

GL.iNet cannot point customers to Rockchip or other suppliers. Each company that distributes GPL software has an independent obligation to provide source code.

## Run Your Own Analysis

Clone the [repository](https://github.com/stvhay/glinet-comet-reverse-gpl) and run:

```bash
nix develop
./scripts/analyze.sh
```

Results go to `output/`. The script downloads the firmware automatically.

## Resources

- [GL.iNet Forum Discussion](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955)
- [GL.iNet KVMD Source](https://github.com/gl-inet/glkvm) (application layer only)
- [Rockchip Open Source](https://opensource.rock-chips.com/)
- [GPL v2 License Text](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
