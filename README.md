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

## Quality Management

This project follows an **ISO 9001:2015-aligned quality management system** adapted for AI-assisted open source development. Every finding in this analysis is traceable to automated scripts with documented methodology—ensuring reproducibility and credibility.

**Key QMS Features:**
- **100% Reproducibility** - All analysis results derive from committed scripts
- **≥60% Test Coverage** - 619+ automated tests validate analysis correctness
- **Dual-Trigger Reviews** - Quality reviews triggered by calendar date OR AI work-hours
- **Evidence-Based Documentation** - Jinja templates auto-cite source scripts for every claim

This rigor is essential for GPL compliance analysis where accuracy directly impacts legal obligations. See **[docs/quality/](docs/quality/)** for complete QMS documentation including quality policy, procedures, and risk management.

## Legal

This repository contains only scripts and documentation. No proprietary code or binaries are included.

## License

**AGPL-3.0 with Military Use Restrictions**

This project is licensed under the GNU Affero General Public License v3.0 with additional restrictions prohibiting military, weapons, and paramilitary use.

- [LICENSE](LICENSE) - Full AGPL-3.0 text
- [LICENSE.ADDENDUM](LICENSE.ADDENDUM) - Additional restrictions
- [RELICENSING.md](RELICENSING.md) - Relicensing notice (from GPL-2.0)

⚠️ **Non-OSI Compliant:** The additional restrictions make this license non-compliant with the Open Source Definition. This is intentional.
