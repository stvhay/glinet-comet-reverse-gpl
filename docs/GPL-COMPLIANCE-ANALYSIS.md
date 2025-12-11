# GPL Compliance Analysis

[← Back to README](../README.md) · [Analysis Reports →](analysis/SUMMARY.md)

---

**GL.iNet has not released the GPL-required source code for the Comet (GL-RM1).**

The firmware contains Linux kernel 4.19.111, U-Boot 2017.09, BusyBox, and other GPL components. Users have requested source code on the GL.iNet forum. As of December 2025, only the application layer (KVMD) has been released.

| Status | Components |
|--------|------------|
| **Not Released** | Linux kernel, U-Boot, BusyBox, bcmdhd WiFi driver |
| **Released** | KVMD application ([github.com/gl-inet/glkvm](https://github.com/gl-inet/glkvm)) |

**Firmware:** glkvm-RM1-1.7.2-1128-1764344791.img
**SHA256:** `6044860b839b7ba74de2ec77b2a0764cd0c16ae27ad0f94deb715429c37e8f19`

---

## Legal Framework

### Copyleft Licenses Overview

Copyleft licenses require that derivative works be distributed under the same or compatible license terms, with source code made available. The key copyleft licenses found in this firmware are:

| License | Type | Source Disclosure Scope |
|---------|------|------------------------|
| GPL-2.0 | Strong copyleft | Entire derivative work |
| GPL-3.0 | Strong copyleft | Entire derivative work |
| LGPL-2.1 | Weak copyleft | Modified library files only |
| LGPL-3.0 | Weak copyleft | Modified library files only |
| MPL-2.0 | File-level copyleft | Modified files only |

### GNU General Public License (GPL)

The GPL requires that anyone who distributes GPL-licensed software (or a derivative work) must make the corresponding source code available to recipients under the same license terms.

**GPL v2 Section 3** states:
> You may copy and distribute the Program (or a work based on it) in object code or executable form... provided that you also do one of the following:
> a) Accompany it with the complete corresponding machine-readable source code...
> b) Accompany it with a written offer, valid for at least three years, to give any third party... a complete machine-readable copy of the corresponding source code...

### GNU Lesser General Public License (LGPL)

The LGPL allows linking with proprietary software but requires:
- Source code for the LGPL library itself (including modifications)
- Object files or source for the proprietary portions sufficient to re-link with modified library
- Clear documentation of how to exercise this right

### Mozilla Public License (MPL)

The MPL requires disclosure of modifications to MPL-licensed files, but allows combining with proprietary code in separate files.

### Obligations Summary

When distributing a product containing copyleft software, the distributor must:

1. Provide complete, corresponding source code for all copyleft components
2. Include any modifications made to copyleft software
3. Provide build instructions sufficient to reproduce the distributed binaries
4. Make source available to any recipient of the binary distribution
5. For LGPL: provide means to re-link with modified libraries

---

## GPL-Licensed Components Identified

### 1. Linux Kernel

| Property | Value |
|----------|-------|
| **Version** | 4.19.111 |
| **License** | GPL-2.0-only |
| **Evidence** | Module vermagic: `4.19.111 SMP preempt mod_unload ARMv7 p2v8` |
| **Platform** | Rockchip RV1126 (ARM Cortex-A7) |

**Source Code Status:** NOT PUBLICLY AVAILABLE

The Linux kernel is the core of the operating system. This specific version (4.19.111) with Rockchip RV1126 support contains:
- Board-specific device tree modifications
- Rockchip-specific drivers and patches
- Build configuration (.config)

**Required Disclosure:**
- Complete kernel source tree
- All Rockchip and GL.iNet modifications
- Device tree source files (.dts)
- Kernel configuration file
- Build instructions

### 2. U-Boot Bootloader

| Property | Value |
|----------|-------|
| **Version** | 2017.09-gfd8bfa2acd-dirty |
| **License** | GPL-2.0+ |
| **Build Date** | Nov 27 2025 - 08:06:12 +0000 |
| **Evidence** | String extracted from decompressed bootloader binary |

**Source Code Status:** NOT PUBLICLY AVAILABLE

The `-dirty` suffix indicates modifications were made beyond the tagged release. The bootloader includes:
- RV1126 board support
- Device tree blob for hardware initialization
- Secure boot configuration (OP-TEE integration)

**Required Disclosure:**
- Complete U-Boot source tree
- Rockchip RV1126 board support code
- U-Boot device tree source
- Build configuration and instructions

### 3. BusyBox

| Property | Value |
|----------|-------|
| **Version** | 1.27.2 |
| **License** | GPL-2.0-only |
| **Build Date** | 2025-11-27 08:14:38 UTC |
| **Evidence** | Version string in binary |

**Source Code Status:** NOT PUBLICLY AVAILABLE (as configured/built)

While upstream BusyBox source is available, the specific configuration used to build this binary determines which applets are included. The build configuration must be provided.

**Required Disclosure:**
- BusyBox source (or reference to upstream version)
- `.config` file showing enabled applets
- Any patches applied
- Build instructions

### 4. GNU Coreutils

| Property | Value |
|----------|-------|
| **License** | GPL-3.0+ |
| **Evidence** | Binary present at `/usr/bin/coreutils` |

**Source Code Status:** NOT PUBLICLY AVAILABLE (as configured/built)

**Required Disclosure:**
- Source code or reference to upstream version
- Build configuration
- Any patches applied

### 5. bcmdhd WiFi Driver

| Property | Value |
|----------|-------|
| **License** | GPL-2.0 (with Broadcom exception) |
| **Location** | `/system/lib/modules/bcmdhd.ko` |
| **Evidence** | Kernel module in firmware |

**Source Code Status:** NOT PUBLICLY AVAILABLE

This is a Broadcom wireless driver that must be distributed with source code when included in a GPL kernel.

**Required Disclosure:**
- Complete driver source code
- Build configuration

### 6. Additional GPL Tools

The following GPL-licensed utilities were identified in the firmware:

| Tool | License | Status |
|------|---------|--------|
| bash | GPL-3.0+ | Source not provided |
| gzip | GPL-3.0+ | Source not provided |
| tar | GPL-3.0+ | Source not provided |
| grep | GPL-3.0+ | Source not provided |
| sed | GPL-3.0+ | Source not provided |
| awk (gawk) | GPL-3.0+ | Source not provided |
| vim | Vim License (GPL-compatible) | Source not provided |

### 7. FFmpeg Libraries (LGPL/GPL)

| Library | Version | License |
|---------|---------|---------|
| libavcodec | 58.35.100 | LGPL-2.1+ (or GPL if built with GPL components) |
| libavformat | 58.20.100 | LGPL-2.1+ |
| libavfilter | 7.40.101 | LGPL-2.1+ |
| libavdevice | 58.5.100 | LGPL-2.1+ |
| libavutil | 56.22.100 | LGPL-2.1+ |

**Source Code Status:** NOT PUBLICLY AVAILABLE

FFmpeg's license depends on build configuration. If built with `--enable-gpl` or linked against GPL libraries (e.g., x264), the entire binary is GPL. Source must be provided either way.

**Required Disclosure:**
- Complete FFmpeg source tree
- Build configuration (configure flags)
- Any patches applied

### 8. LGPL-Licensed Libraries

The following libraries are under LGPL, requiring source code for the library (including modifications) and means to re-link:

| Library | Version | License |
|---------|---------|---------|
| glibc | 2.28 | LGPL-2.1+ |
| libstdc++ | 6.0.25 | GPL-3.0 with Runtime Exception |
| GLib | 2.64.4 | LGPL-2.1+ |
| D-Bus | 3.19.4 | GPL-2.0+ or AFL-2.1 |
| BlueZ (libbluetooth) | 3.18.16 | GPL-2.0+ |
| ALSA lib | 2.0.0 | LGPL-2.1+ |
| libdrm | 2.4.0 | MIT (permissive) |
| libcurl | 4.7.0 | MIT/X derivate |
| OpenSSL | 1.1 | OpenSSL License / Apache 2.0 |
| GnuTLS | 30.14.9 | LGPL-2.1+ |
| nettle | 6.4 | LGPL-3.0+ / GPL-2.0+ |
| libevent | 2.1 | BSD-3-Clause |
| Janus Gateway | 2.0.6 | GPL-3.0 |
| live555 | - | LGPL-3.0 |
| libmad | 0.2.1 | GPL-2.0 |

**Note:** BlueZ, D-Bus, libmad, and Janus Gateway are GPL-licensed, requiring full source disclosure.

**Source Code Status:** NOT PUBLICLY AVAILABLE (as configured/built)

**Required Disclosure:**
- Source code for all LGPL/GPL libraries
- Build configurations
- Means to re-link (object files or source for proprietary portions)

---

## Build System Analysis

| Property | Value |
|----------|-------|
| **Build System** | Buildroot 2018.02-rc3 |
| **Buildroot Commit** | gd56bbacb |
| **SDK Base** | Rockchip RV1126/RV1109 Linux SDK |

The firmware is built using Buildroot, which is itself GPL-licensed. The complete Buildroot configuration, including:
- Package selections
- Kernel configuration
- Toolchain configuration
- Custom packages

...should be provided to enable recipients to reproduce the build.

---

## What Has Been Released

GL.iNet has released the following on GitHub:

### KVMD Application (gl-inet/glkvm)
- **License:** GPL-3.0
- **Contents:** Application-layer daemon (Python, JavaScript, C)
- **URL:** https://github.com/gl-inet/glkvm

This repository contains only the userspace KVMD application, which is a derivative of the PiKVM project. It does **not** contain:
- Linux kernel source
- U-Boot source
- Buildroot configuration
- Device tree sources
- Kernel module sources

---

## What Must Be Released

To comply with copyleft license requirements, GL.iNet and/or Rockchip must provide:

### Critical Priority (GPL-2.0 - Legally Required)

1. **Linux Kernel 4.19.111**
   - Complete source tree
   - Rockchip RV1126 board support
   - All patches and modifications
   - Device tree source (.dts files)
   - Kernel .config file
   - Build instructions

2. **U-Boot 2017.09**
   - Complete source tree
   - RV1126 board configuration
   - Device tree source
   - Build instructions

3. **bcmdhd WiFi Driver**
   - Complete driver source
   - Makefile/build configuration

4. **BusyBox 1.27.2**
   - Source code (or upstream reference)
   - .config file
   - Any patches

5. **BlueZ Bluetooth Stack**
   - Source code
   - Build configuration

6. **libmad (MPEG Audio Decoder)**
   - Source code
   - Build configuration

### High Priority (GPL-3.0 - Legally Required)

7. **GNU Coreutils, bash, gzip, tar, grep, sed, gawk**
   - Source or upstream version reference
   - Build configuration
   - Any patches

8. **Janus WebRTC Gateway**
   - Complete source code
   - Build configuration
   - Plugins source

### Medium Priority (LGPL - Legally Required)

9. **FFmpeg (libavcodec, libavformat, etc.)**
   - Complete source tree
   - Configure flags used
   - Any patches

10. **glibc 2.28**
    - Source or upstream reference
    - Build configuration
    - Object files for re-linking (or source for proprietary code)

11. **GLib, GnuTLS, nettle, ALSA lib, live555**
    - Source code
    - Build configuration

### Build System (Required for Reproducibility)

12. **Buildroot 2018.02-rc3**
    - Complete configuration
    - Custom package definitions
    - Build scripts
    - Toolchain configuration

---

## Source Code Request Template

The following may be used as a formal GPL source code request:

---

**To:** GL.iNet Support / Legal Department
**Subject:** GPL Source Code Request - GL-RM1 Comet Firmware v1.7.2

Dear GL.iNet,

Pursuant to the GNU General Public License versions 2 and 3, I am requesting the complete corresponding source code for the GPL-licensed software distributed in the GL.iNet Comet (GL-RM1) device, firmware version 1.7.2.

Specifically, I request source code for:

1. Linux kernel 4.19.111 (GPL-2.0), including:
   - Complete kernel source tree
   - Rockchip RV1126 platform support code
   - Device tree sources (.dts files)
   - Kernel configuration (.config)
   - Build instructions

2. U-Boot 2017.09-gfd8bfa2acd (GPL-2.0+), including:
   - Complete U-Boot source tree
   - Board support code
   - Device tree sources
   - Build instructions

3. BusyBox 1.27.2 (GPL-2.0), including:
   - Source code and configuration

4. bcmdhd WiFi driver (GPL-2.0), including:
   - Complete driver source code

5. GNU Coreutils, bash, gzip, tar, grep, sed, gawk (GPL-3.0+)

6. Buildroot 2018.02-rc3 configuration used to build the firmware

As a recipient of GPL-licensed binaries, I am entitled to receive this source code under the terms of the GPL. Please provide instructions for obtaining this source code.

Sincerely,
[Your Name]

---

## Responsible Parties

Under GPL, **each entity in the distribution chain that commercially distributes GPL software has its own independent obligation to comply**. A manufacturer cannot simply rely on their upstream vendor's source code offer - they must provide their own compliant offer when distributing to customers.

### GL.iNet (Shenzhen GL Technologies Co., Ltd.)

| Attribute | Value |
|-----------|-------|
| **Role** | Device manufacturer and firmware distributor to end users |
| **Legal Obligation** | **Must provide GPL source code to any customer who receives the device** |
| **Cannot Delegate** | GL.iNet cannot simply point customers to Rockchip; they must provide source themselves |
| **Website** | https://www.gl-inet.com |
| **Support** | https://www.gl-inet.com/support/ |

**GL.iNet is the primary party responsible for GPL compliance** because they are the entity distributing GPL-licensed binaries to end users (customers). Even if Rockchip provided pre-compiled binaries, GL.iNet has an independent obligation to provide source code.

### Rockchip Electronics Co., Ltd.

| Attribute | Value |
|-----------|-------|
| **Role** | SoC vendor, SDK provider to manufacturers |
| **Obligation to GL.iNet** | Should provide SDK source code to GL.iNet |
| **Obligation to End Users** | Generally none, unless Rockchip directly distributes to end users |
| **SDK** | Rockchip RV1126/RV1109 Linux SDK |

Rockchip's primary obligation is to provide source code to their direct customers (GL.iNet and other manufacturers). However, if Rockchip's license agreements prevent GL.iNet from redistributing the source, this does not excuse GL.iNet from GPL compliance - it means GL.iNet should not have distributed the binaries.

### Legal Basis

From the [Software Freedom Law Center's GPL Compliance Guide](https://softwarefreedom.org/resources/2008/compliance-guide.html):

> "The license terms apply to anyone who distributes GPL'd software, regardless of whether they are the original distributor... Commercial redistributors cannot avail themselves of the option (c) exception, and so while your offer for source must be good to anyone who receives the offer (under v2) or the object code (under v3), it cannot extinguish the obligations of anyone who commercially redistributes your product."

---

## Evidence Documentation

This analysis is based on technical examination of:

1. **Firmware image:** `glkvm-RM1-1.7.2-1128-1764344791.img`
   - Source: https://fw.gl-inet.com/kvm/rm1/release/
   - SHA256: `6044860b839b7ba74de2ec77b2a0764cd0c16ae27ad0f94deb715429c37e8f19`

2. **Extraction tools:** binwalk, unsquashfs, dtc

3. **Analysis repository:** https://github.com/stvhay/glinet-comet-reverse-gpl

Supporting evidence files:
- [Kernel Version Analysis](analysis/kernel-version.md)
- [U-Boot Version Analysis](analysis/uboot-version.md)
- [GPL Binaries List](analysis/gpl-binaries.md)
- [Device Tree Analysis](analysis/device-trees.md)
- [Build Information](analysis/build-info.md)

---

## References

- [GNU General Public License v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
- [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html)
- [BusyBox License](https://busybox.net/license.html)
- [GL.iNet Forum Discussion on Open Source](https://forum.gl-inet.com/t/comet-gl-rm1-and-open-source/55955)
- [GL.iNet GLKVM GitHub Repository](https://github.com/gl-inet/glkvm)
- [Rockchip Open Source Documentation](https://opensource.rock-chips.com/)
- [Rockchip U-Boot Repository](https://github.com/rockchip-linux/u-boot)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.3 | December 2025 | Initial analysis; added LGPL components, FFmpeg, clarified responsible parties |
