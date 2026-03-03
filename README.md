# GL.iNet Comet GPL Compliance Analysis

[![CI](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml/badge.svg)](https://github.com/stvhay/glinet-comet-reverse-gpl/actions/workflows/ci.yml)
[![Live Status](https://img.shields.io/badge/status-live%20updates-blue)](https://gist.github.com/stvhay/165f51b518db358f3515610af94e01fb)

---

> **PROJECT PAUSED** — December 2025
>
> This project is currently on hold due to other priorities. The initial goal of identifying GPL compliance issues has been **partially achieved** — GL.iNet has [published](https://github.com/gl-inet/kernel-4.19) [source repositories](https://github.com/gl-inet/buildroot-2018) but they contain only unmodified Rockchip BSP code without RM1-specific configurations, device trees, or build instructions. U-Boot source remains unpublished. See open issues on [kernel-4.19](https://github.com/gl-inet/kernel-4.19/issues/1) and [buildroot-2018](https://github.com/gl-inet/buildroot-2018/issues/1).
>
> **Potential Purpose Evolution:** This project may evolve into a pilot for validating agentic ISO 9001 QMS tooling implementation using ARM board reverse engineering as the application domain.
>
> **Status:** Work may resume when priorities allow. For questions or interest in the QMS tooling work, please open an issue.

---

**GL.iNet ships GPL-licensed software in their Comet KVM device. In January 2026, they published kernel and Buildroot repositories, but these contain only unmodified Rockchip BSP code — the RM1-specific modifications, configurations, and build instructions required for GPL compliance have not been released.** <!-- cite: results/bsp_repos.toml#kernel_rm1_dts_found --> <!-- cite: results/bsp_repos.toml#buildroot_rm1_defconfig_found -->

This project analyzes the firmware to document what source code GL.iNet must provide under the GPL license.

## Key Findings

The Comet (GL-RM1) contains at least 10 GPL-licensed components. GL.iNet has published base Rockchip BSP source for several, but none include the RM1-specific modifications needed for GPL compliance.

| Component | License | Source Released? | Notes |
|-----------|---------|:---:|---|
| Linux Kernel 4.19.111 | GPL-2.0 | :x: No | [Base BSP published](https://github.com/gl-inet/kernel-4.19), RM1 config/DTS missing <!-- cite: results/bsp_repos.toml#kernel_rm1_dts_found --> |
| U-Boot 2017.09 | GPL-2.0+ | :x: No | Not published |
| BusyBox 1.27.2 | GPL-2.0 | :x: No | In [BSP Buildroot](https://github.com/gl-inet/buildroot-2018), RM1 config missing |
| GNU Coreutils | GPL-3.0+ | :x: No | In BSP Buildroot, RM1 config missing |
| bcmdhd WiFi Driver | GPL-2.0 | :x: No | In BSP kernel tree, build config missing |
| FFmpeg 58.x | LGPL-2.1+ | :x: No | In BSP Buildroot, configure flags missing |
| BlueZ 3.18.16 | GPL-2.0+ | :x: No | In BSP Buildroot, RM1 config missing |
| Janus Gateway 2.0.6 | GPL-3.0 | :x: No | In BSP Buildroot, RM1 config missing |
| glibc 2.28 | LGPL-2.1+ | :x: No | BSP has 2.29; firmware uses 2.28 from external toolchain |
| Buildroot 2018.02-rc3 | GPL-2.0+ | :x: No | [BSP published](https://github.com/gl-inet/buildroot-2018), RM1 defconfig missing <!-- cite: results/bsp_repos.toml#buildroot_rm1_defconfig_found --> |
| KVMD Application | GPL-3.0 | :white_check_mark: [Yes](https://github.com/gl-inet/glkvm) | |

Users have [requested source code on the GL.iNet forum](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955). As of March 2026, GL.iNet has published base Rockchip BSP repositories but has not provided the RM1-specific source code or build configurations needed for compliance.

## Who Must Provide Source Code?

GL.iNet must provide source code to any customer who requests it. This is their legal obligation under the GPL. They cannot point customers to Rockchip or other suppliers—each distributor has an independent obligation.

**[Read the full compliance analysis →](docs/GPL-COMPLIANCE-ANALYSIS.md)**

## Run Your Own Analysis

```bash
nix develop
./scripts/analyze.sh
```

Results go to `output/`. See the **[Wiki](https://github.com/stvhay/glinet-comet-reverse-gpl/wiki)** for detailed usage and analysis reports.

## Contributing

Contributions are welcome! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:
- Quick start guide (nix develop, running tests)
- Black box methodology principles
- Issue templates and contribution workflow
- Code quality standards
- Path to maintainership

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

- [LICENSE.md](LICENSE.md) - Full AGPL-3.0 text
- [LICENSE.ADDENDUM.md](LICENSE.ADDENDUM.md) - Additional restrictions
- [RELICENSING.md](RELICENSING.md) - Relicensing notice (from GPL-2.0)

**Non-OSI Compliant:** The additional restrictions make this license non-compliant with the Open Source Definition. This is intentional.
