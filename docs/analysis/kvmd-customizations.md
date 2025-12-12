# GL.iNet KVMD Customizations

## Overview

This document analyzes the customizations GL.iNet made to PiKVM's KVMD (Keyboard-Video-Mouse Daemon) for their Comet (GL-RM1) KVM-over-IP device.

**Analysis Date:** 2025-12-11
**GL.iNet Repository:** https://github.com/gl-inet/glkvm
**Upstream Repository:** https://github.com/pikvm/kvmd
**License:** GPL-3.0 (both repositories)

## What is KVMD?

KVMD is the main daemon powering PiKVM, an open-source KVM-over-IP solution originally designed for Raspberry Pi. KVMD provides:

- Remote keyboard and mouse control via HID emulation
- Video capture and streaming
- Mass storage device emulation
- ATX power control
- Web-based management interface
- VNC and IPMI interfaces

GL.iNet has forked KVMD to create GLKVM, their commercial KVM-over-IP product based on the Comet hardware.

## Repository Comparison

### Version Information

- **GL.iNet Version:** v1.7.2 (as of December 2025)
  - Based on KVMD v4.16
  - 3,476 commits
  - 31 contributors
- **Upstream PiKVM:** v4.132 (as of December 2025)
  - 3,975 commits
  - 58 contributors
  - Active development with frequent releases

**Key Observation:** GL.iNet forked from an earlier version of KVMD (v4.16) and has not merged upstream changes since then. The upstream is now at v4.132, indicating GL.iNet maintains an independent fork with 116 versions of divergence.

### Repository Structure

Both repositories share the same basic structure:

```
├── .github/          # CI/CD workflows
├── configs/          # Configuration files (janus, kvmd, nginx, os)
├── contrib/          # Community contributions
├── extras/           # Additional resources
├── hid/              # HID implementation
├── kvmd/             # Core daemon code
│   ├── apps/         # Application modules
│   ├── clients/      # Client implementations
│   ├── helpers/      # Utility helpers
│   ├── keyboard/     # Keyboard handling
│   ├── plugins/      # Plugin system
│   │   ├── atx/      # ATX power control
│   │   ├── auth/     # Authentication
│   │   ├── hid/      # HID plugins
│   │   ├── msd/      # Mass storage device
│   │   └── ugpio/    # GPIO utilities
│   ├── validators/   # Input validation
│   └── yamlconf/     # YAML configuration
├── scripts/          # Utility scripts
├── testenv/          # Testing environment (upstream only)
└── web/              # Web interface
    ├── extras/
    ├── ipmi/
    ├── kvm/
    ├── login/
    ├── share/
    └── vnc/
```

**Language Distribution:**
- GL.iNet: Python 68%, JavaScript 9%, HTML 6.2%, C 4.9%, CSS 3.4%, C++ 3.4%
- Upstream: Python 63.9%, JavaScript 11.4%, HTML 7.3%, C/C++ 8.6%

The similar language distribution indicates GL.iNet has maintained the core architecture.

## Hardware Abstraction Differences

### Target Hardware

**GL.iNet Comet (GL-RM1):**
- **SoC:** Rockchip RV1126 (quad-core Cortex-A7 @ 1.5GHz)
- **RAM:** 1GB DDR3 (2x Winbond 512MB)
- **Storage:** 8GB eMMC 5.1 (Toshiba THGBMUG6C1LBAIL)
- **Network:** Gigabit Ethernet (RealTek RTL8211F)
- **Video:** HDMI to MIPI CSI bridge (RV1126 is camera-focused)
- **USB:** DWC3 controller at address 0xffd00000
- **Power:** 5V/2A USB-C

**PiKVM (Raspberry Pi):**
- **SoC:** Broadcom BCM2711 (Raspberry Pi 4) or similar
- **Video:** Native HDMI or CSI camera input
- **USB:** BCM2835/BCM2711 USB OTG

### HID Implementation Differences

The HID plugin structure is identical in both repositories, supporting multiple transport methods:

- `otg/` - USB OTG gadget mode (primary for both)
- `ch9329/` - CH9329 HID chip
- `bt/` - Bluetooth HID
- `serial.py` - Serial HID
- `spi.py` - SPI HID

**GL.iNet-Specific OTG Implementation:**

GL.iNet's HID OTG plugin monitors USB connection state via a Rockchip-specific sysfs path:

```python
"/sys/kernel/debug/ffd00000.dwc3/link_state"
```

This path is specific to the DWC3 USB controller in the Rockchip RV1126 at memory address `0xffd00000`. The upstream PiKVM uses Raspberry Pi-specific paths for the BCM USB controllers.

**Device Files:**
- Keyboard HID: `/dev/hidg0`
- Mouse HID: `/dev/hidg1`

These are standard Linux USB gadget device files used by both implementations.

### GPIO Abstraction

Both repositories use a modular GPIO plugin system (`kvmd/plugins/ugpio/`) that supports:
- Input/output modes
- Debouncing
- Pin validation
- Driver-specific implementations

The base architecture is unchanged, but GL.iNet likely uses Rockchip GPIO drivers instead of BCM GPIO drivers.

### Video Capture

The Rockchip RV1126 is a camera-focused SoC with MIPI CSI interfaces but no native HDMI input. GL.iNet uses an **HDMI to MIPI CSI bridge** to adapt HDMI video to the RV1126's camera input pipeline.

This is a significant hardware difference from Raspberry Pi, which can use:
- Native HDMI input (on certain HATs)
- CSI camera modules
- USB capture cards

The video capture implementation differences are not visible in the KVMD repository itself, as these likely reside in:
- Kernel drivers
- Device tree configurations
- Janus WebRTC streaming configuration
- Hardware-specific capture utilities

## GL.iNet-Specific Features

Based on release notes and commit history, GL.iNet has added several features:

### 1. Cloud Services (v1.5.0)

- **Remote browser access** support
- **Private cloud service deployment** capability
- Integration with **AstroWarp cloud service** (proprietary GL.iNet service)

**Note:** Code for these features is not visible in the public glkvm repository search results, suggesting:
- Implementation may be in configuration files
- Integration may be external to KVMD
- Some components may be proprietary

### 2. Tailscale Integration (v1.4.2)

- Exit Node functionality
- Static configuration support

Tailscale provides secure remote access via WireGuard VPN. This feature is not present in upstream PiKVM.

### 3. Enhanced Audio (v1.3.0 - v1.4.2)

- **OPUS audio codec** support
- Fixed "OPUS mono audio in Chrome" issue
- **Microphone audio transmission** capability

Upstream PiKVM supports audio, but GL.iNet has made specific improvements for:
- Browser compatibility
- Bidirectional audio (microphone input)

### 4. Direct H.264 Transmission (v1.4.2)

- **"Direct H.264 transmission mode"** for improved video streaming
- Leverages hardware encoding capabilities of RV1126

The RV1126's integrated H.264/H.265 encoder allows for more efficient video streaming than software encoding. This is a hardware-specific optimization.

### 5. User Interface Enhancements (v1.3.0)

- **Customizable keyboard shortcuts**
- **Virtual keyboard repositioning**
- **Clipboard multilingual support**
- **Mouse sensitivity adjustments** with direction reversal
- **Timezone adjustment** capabilities
- **Device identity customization**

### 6. Network Discovery (2024 commits)

- **Avahi integration** for mDNS/DNS-SD service discovery
- Service enablement and dependency management
- Hostname: `glkvm.local`

### 7. Deployment Tooling

GL.iNet added `apply_to_glkvm.sh` for development/deployment:

```bash
#!/bin/bash
# Synchronizes local kvmd changes to remote device

REMOTE_HOST="glkvm.local"
REMOTE_DIR="/usr/lib/python3.12/site-packages/kvmd/"
REMOTE_USER="root"
LOCAL_DIR="kvmd"

# Clear existing files
ssh root@glkvm.local "rm $REMOTE_DIR/* -R"

# Upload new files
scp -r $LOCAL_DIR/* root@glkvm.local:$REMOTE_DIR

# Restart required
echo "Restart the kvm device to make the configuration take effect"
```

This enables rapid iteration during development by directly replacing the KVMD Python package on the device.

### 8. Platform-Specific Fixes

- **Linux EDID compatibility** improvements (v1.3.1)
- **IPv6 support** (v1.3.1)
- **Intel graphics audio output** corrections (v1.2.3)
- **UI rendering** enhancements (v1.1.1)

## Removed or Modified Functionality

Based on available information, GL.iNet has **not removed major functionality** from KVMD. The fork maintains compatibility with the core PiKVM feature set while adding proprietary enhancements.

**Potential Modifications:**

1. **Platform-specific code removal** - Code specific to Raspberry Pi GPIO, USB, or video capture may be disabled or removed in favor of Rockchip equivalents

2. **Update mechanism** - GL.iNet added their own firmware upgrade API support rather than using PiKVM's update system

3. **Certificate defaults** - Changed default country code to "US" in certificate generation

4. **OLED support** - Upstream has extensive OLED display support (`kvmd/apps/oled/`). GL.iNet's commit history mentions "OLED sensor class implementation" but specifics are unclear. The Comet hardware does not appear to have an OLED display based on specifications.

## GPL Compliance Implications

### License Adherence

GL.iNet **explicitly acknowledges** PiKVM and commits to GPL-3.0 compliance in their README:

> "GLKVM KVMD is a derivative project based on the open-source PiKVM. We are grateful to the PiKVM team for their contributions and are committed to complying with all terms of the GPL V3 license."

The glkvm repository is **publicly available** under GPL-3.0, satisfying the license's requirement for source code availability.

### Compliance Requirements

Under GPL-3.0, GL.iNet must:

1. **Provide source code** for all GPL-licensed components ✓
   - KVMD source is available at https://github.com/gl-inet/glkvm

2. **Preserve copyright notices** ✓
   - Repository maintains original author attribution (Maxim Devaev)

3. **Distribute under same license** ✓
   - Repository is GPL-3.0 licensed

4. **Provide complete corresponding source** ?
   - The glkvm repository contains KVMD userspace code
   - **Missing:** Kernel drivers, device trees, bootloader, and other GPL components
   - These should be available per GPL requirements (see other analysis documents)

5. **Disclose modifications** ?
   - Repository contains modified code
   - No explicit changelog documenting all changes from upstream
   - Commit history provides some insight but is not comprehensive

### Proprietary Additions

GL.iNet has added proprietary features that are **not in the public repository**:

- AstroWarp cloud service integration
- Potentially some firmware update mechanisms
- Possibly some UI/UX enhancements

**This is permissible** under GPL-3.0 as long as:
- The proprietary code is **separate** from GPL code
- The GPL code remains available and functional
- Proprietary additions are not **derivative works** of GPL code

If the proprietary additions are tightly integrated with KVMD (derivative works), they may need to be released under GPL-3.0. This requires legal analysis beyond the scope of this technical document.

### Recommendations for Full Compliance

1. **Provide comprehensive source release** including:
   - Kernel source with all drivers and patches
   - U-Boot source with configurations
   - Device tree sources
   - Build scripts and toolchain information
   - All GPL-licensed components from the firmware

2. **Document modifications** clearly:
   - Maintain a detailed changelog vs upstream
   - Tag releases corresponding to firmware versions
   - Document hardware-specific changes

3. **Clarify proprietary boundaries**:
   - Clearly document which features are proprietary
   - Ensure separation between GPL and proprietary code
   - Provide functional GPL-only build if possible

4. **Sync with upstream** or clearly communicate fork status:
   - Currently 116 versions behind upstream (v4.16 vs v4.132)
   - Security and bug fixes from upstream are not incorporated
   - Consider periodic merges or document divergence rationale

## Technical Architecture Summary

GL.iNet's GLKVM maintains the core PiKVM architecture:

- **Base OS:** Arch Linux
- **Daemon:** KVMD (forked at v4.16)
- **Web Server:** Nginx
- **Streaming:** Janus WebRTC Gateway
- **HID:** USB OTG gadget mode
- **Language:** Python 3.12

**Key Customizations:**
- Hardware abstraction for Rockchip RV1126
- USB controller path: `/sys/kernel/debug/ffd00000.dwc3/link_state`
- HDMI to MIPI CSI bridge for video capture
- Hardware H.264 encoding support
- Cloud service integration (proprietary)
- Enhanced audio support (OPUS, microphone)
- Tailscale VPN integration
- Improved UI/UX features

**Deployment Model:**
- eMMC boot with 8GB storage
- Python packages in `/usr/lib/python3.12/site-packages/kvmd/`
- Configuration in `/configs/`
- SSH access for development (root@glkvm.local)

## Conclusion

GL.iNet has created a functional fork of PiKVM's KVMD, adapting it for their Rockchip RV1126-based hardware while adding commercial features. The core GPL-3.0 components are publicly available, satisfying the primary license requirements.

**Strengths:**
- Clear GPL-3.0 compliance statement
- Public source repository
- Maintains upstream attribution
- Functional derivative work

**Areas for Improvement:**
- Provide complete source including kernel and bootloader
- Document all modifications comprehensively
- Consider syncing with upstream for security updates
- Clarify licensing boundaries for proprietary features

The customizations are primarily hardware adaptations (Rockchip vs Broadcom) and value-added features (cloud services, enhanced audio/video) rather than fundamental architectural changes.

## References

- GL.iNet KVMD Repository: https://github.com/gl-inet/glkvm
- Upstream PiKVM: https://github.com/pikvm/kvmd
- GL.iNet Comet Product Page: https://www.gl-inet.com/products/gl-rm1/
- GL.iNet Comet Documentation: https://docs.gl-inet.com/kvm/en/user_guide/gl-rm1/
- CNX Software Review: https://www.cnx-software.com/2025/07/13/review-of-gl-inet-comet-gl-rm1-kvm-over-ip-solution-and-atx-power-control-board/
- Security Analysis: https://www.runzero.com/blog/oob-p1-ip-kvm/

## Appendix: Commit History Analysis

Key commit patterns from GL.iNet (2024-2025):

- **Version releases:** 1.1.0 → 1.1.1 → 1.2.3 → 1.3.0 → 1.3.1 → 1.4.2 → 1.5.0 → 1.7.2
- **Audio improvements:** "Fixed OPUS mono audio in Chrome"
- **Device discovery:** Avahi integration and configuration
- **Hardware support:** OLED sensor class
- **Network features:** STUN configuration by IP address
- **Code quality:** Refactoring, removed debug prints
- **Certificates:** Updated default country to US
- **Infrastructure:** Automatic KVMD configuration scripts

The commit history shows **incremental improvements** focused on stability, compatibility, and feature additions rather than architectural rewrites.
