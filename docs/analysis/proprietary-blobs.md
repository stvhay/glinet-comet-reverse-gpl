# Proprietary Rockchip Libraries

[← Analysis Reports](SUMMARY.md)

---

The firmware contains Rockchip media libraries for hardware-accelerated video encoding. Most critical libraries (MPP, RGA) are actually open source under Apache 2.0.

**Platform:** Rockchip RV1126

## Key Findings

| Library | Purpose | License | Required |
|---------|---------|---------|----------|
| librockchip_mpp.so | Video encoding | Apache 2.0 | Critical |
| librga.so | 2D graphics | Apache 2.0 | High |
| libeasymedia.so | Media framework | Apache 2.0 | High |
| libRKAP_3A.so | Audio processing | Proprietary | Medium |
| librkdb.so | Vendor storage | Proprietary | Medium |

**Good news:** The video encoding stack (MPP, RGA) is open source. Only audio processing and vendor storage libraries are proprietary.

---

## Detailed Inventory

## Proprietary Library Inventory

### Media Processing Platform (MPP)

#### 1. librockchip_mpp.so.0
- **Full Path**: `/usr/lib/librockchip_mpp.so.0`
- **Vendor**: Rockchip
- **Purpose**: Media Process Platform - Hardware abstraction layer for video codec acceleration
- **Functionality**:
  - Video encoding (H.264/H.265/VP8/VP9)
  - Video decoding (hardware-accelerated)
  - Interface between user-space applications and kernel video drivers
  - Supports all Rockchip VPU/VEPU/RKVENC/RKVDEC hardware blocks
- **Size**: ~200-500 KB (typical)
- **Architecture**: ARM 32-bit
- **Required For**: CRITICAL - H.264 video encoding for KVM video stream
- **Open Source Status**: **OPEN SOURCE (Apache 2.0)**
  - Source: [github.com/rockchip-linux/mpp](https://github.com/rockchip-linux/mpp)
  - Note: Both kernel driver and user-mode library are open source
  - License: Apache License 2.0
- **Alternatives**:
  - V4L2 stateless video API (Linux kernel upstream, but limited codec support)
  - Software encoding with FFmpeg (significantly slower, high CPU usage)
  - libv4l-rkmpp wrapper (V4L2 compatibility layer over MPP)

#### 2. librockchip_vpu.so.0
- **Full Path**: `/usr/lib/librockchip_vpu.so.0`
- **Vendor**: Rockchip
- **Purpose**: Legacy VPU (Video Processing Unit) library
- **Functionality**:
  - Older API for video encoding/decoding
  - Superseded by librockchip_mpp on newer SoCs
  - May be used for backward compatibility
- **Required For**: OPTIONAL - Legacy application compatibility
- **Open Source Status**: Partially open (older codebase)
- **Alternatives**: Use librockchip_mpp.so instead (modern replacement)
- **Recommendation**: Can likely be removed, replaced by MPP

### 2D Graphics Acceleration (RGA)

#### 3. librga.so.2.1.0
- **Full Path**: `/usr/lib/librga.so.2.1.0`
- **Vendor**: Rockchip
- **Purpose**: Raster Graphics Acceleration - 2D graphics operations
- **Functionality**:
  - Image scaling and rotation
  - Color space conversion (YUV to RGB, etc.)
  - Image composition and blending
  - Format conversion for video pipeline
  - Hardware-accelerated 2D operations
- **Hardware**: RK3588 has 2x RGA3 cores + 1x RGA2 core
- **Required For**: HIGH - Video format conversion, image scaling
- **Open Source Status**: **OPEN SOURCE (Apache 2.0)**
  - Source: [github.com/airockchip/librga](https://github.com/airockchip/librga)
  - License: Apache License 2.0
  - Actively maintained by Rockchip
- **Alternatives**:
  - Software conversion with FFmpeg swscale (much slower)
  - OpenGL ES shaders (requires GPU, more complex)
  - libyuv (Google's CPU-based conversion, slower than RGA)
- **Notes**:
  - Critical for efficient video pipeline
  - Enables low-latency video conversion
  - RK3588-specific: Multiple RGA cores may cause image shift between scaling algorithms

### Image Signal Processing (ISP)

#### 4. librkisp_api.so
- **Full Path**: `/usr/lib/librkisp_api.so`
- **Vendor**: Rockchip
- **Purpose**: ISP (Image Signal Processor) API library
- **Functionality**:
  - Camera sensor control and configuration
  - 3A algorithms (Auto Exposure, Auto White Balance, Auto Focus) interface
  - Image quality tuning
  - Raw image processing pipeline control
  - Camera calibration data management
- **Required For**: OPTIONAL - Only if HDMI input uses ISP features (unlikely)
- **Open Source Status**: **PARTIALLY OPEN**
  - V4L2 driver: rockchip-isp1 (open source, in mainline Linux)
  - Userspace library: Proprietary tuning and 3A integration
  - Detailed specs: Available only under NDA
- **Alternatives**:
  - V4L2 rockchip-isp1 driver (basic ISP control)
  - libcamera (Linux camera stack, limited Rockchip support)
- **Notes**:
  - Likely not needed for HDMI capture (uses video input, not camera)
  - May be included as dependency of other libraries
  - Could be removed if no camera features are used

### Audio Processing (RKAP)

#### 5. libRKAP_3A.so
- **Full Path**: `/usr/lib/libRKAP_3A.so`
- **Vendor**: Rockchip
- **Purpose**: Rockchip Audio Processing - 3A (AEC, AGC, ANR)
- **Functionality**:
  - AEC: Acoustic Echo Cancellation
  - AGC: Automatic Gain Control
  - ANR: Automatic Noise Reduction (same as libRKAP_ANR)
  - Voice processing algorithms
- **Required For**: MEDIUM - Audio quality enhancement for KVM
- **Open Source Status**: **PROPRIETARY**
- **Alternatives**:
  - WebRTC audio processing library (open source, AEC/AGC/ANR)
  - PulseAudio echo cancellation module (limited)
  - Speex DSP library (open source, less advanced)
- **Notes**:
  - Improves audio quality in remote KVM sessions
  - Not strictly required for basic functionality
  - Software alternatives exist but may have different quality

#### 6. libRKAP_ANR.so
- **Full Path**: `/usr/lib/libRKAP_ANR.so`
- **Vendor**: Rockchip
- **Purpose**: Automatic Noise Reduction (subset of RKAP_3A)
- **Functionality**:
  - Noise suppression for audio capture
  - May be standalone or used by RKAP_3A
- **Required For**: LOW - Audio quality enhancement
- **Open Source Status**: **PROPRIETARY**
- **Alternatives**: Same as libRKAP_3A

#### 7. libRKAP_Common.so
- **Full Path**: `/usr/lib/libRKAP_Common.so`
- **Vendor**: Rockchip
- **Purpose**: Common code for RKAP audio libraries
- **Functionality**:
  - Shared routines for RKAP_3A and RKAP_ANR
  - Audio buffer management
  - Common audio DSP functions
- **Required For**: LOW - Dependency of other RKAP libraries
- **Open Source Status**: **PROPRIETARY**
- **Alternatives**: Not applicable (dependency)

### Vendor Storage

#### 8. librkdb.so
- **Full Path**: `/usr/lib/librkdb.so`
- **Vendor**: Rockchip
- **Purpose**: Rockchip Database/Vendor Storage Access
- **Functionality**:
  - Access to vendor-specific storage partition
  - Device configuration and calibration data
  - MAC address, serial number, production data
  - Persistent settings storage
- **Required For**: MEDIUM - Device-specific configuration
- **Open Source Status**: **PROPRIETARY**
- **Alternatives**:
  - Direct access to vendor storage partition (requires reverse engineering)
  - Alternative storage methods (filesystem, u-boot env)
- **Notes**:
  - Often used for factory calibration data
  - May contain device-unique information
  - Reverse engineering possible but complex

#### 9. librkuvc.so
- **Full Path**: `/usr/lib/librkuvc.so`
- **Vendor**: Rockchip
- **Purpose**: Rockchip UVC (USB Video Class) library
- **Functionality**:
  - USB gadget mode for UVC device emulation
  - Allows device to present as USB webcam
  - Video streaming over USB
- **Required For**: OPTIONAL - USB video output feature
- **Open Source Status**: **PARTIALLY OPEN**
  - Linux UVC gadget driver: Open source (in kernel)
  - Rockchip UVC library: Wrapper around kernel driver
- **Alternatives**:
  - Direct use of Linux UVC gadget driver (configfs)
  - Custom implementation using kernel UVC API
- **Notes**:
  - Not required for KVM-over-IP (uses network)
  - Useful if device has USB gadget port for direct connection

### Media Integration

#### 10. libeasymedia.so.1.0.1
- **Full Path**: `/usr/lib/libeasymedia.so.1.0.1`
- **Vendor**: Rockchip
- **Purpose**: Easy Media API - High-level media framework
- **Functionality**:
  - Abstraction layer over MPP, RGA, ISP
  - Simplified API for common media operations
  - Pipeline management for video capture/encoding
  - Integration glue for Rockchip media stack
- **Required For**: HIGH - Likely used by uStreamer and KVMD
- **Open Source Status**: **OPEN SOURCE (Apache 2.0)**
  - Source: [github.com/rockchip-linux/rkmedia](https://github.com/rockchip-linux/rkmedia) or similar
  - License: Apache 2.0 (typical for Rockchip media libraries)
- **Alternatives**:
  - Direct use of MPP/RGA APIs (more complex)
  - GStreamer with Rockchip plugins
  - Custom media pipeline
- **Notes**:
  - Simplifies integration of multiple Rockchip libraries
  - Reduces development complexity
  - May be specific to Rockchip SDK

### AIQ (Rockchip AIQ is for camera tuning, not general AI)

#### 11. librkaiq.so
- **Full Path**: `/usr/lib/librkaiq.so`
- **Vendor**: Rockchip
- **Purpose**: Rockchip Auto Image Quality (AIQ) - Camera tuning
- **Functionality**:
  - Advanced ISP tuning algorithms
  - Image quality optimization
  - Scene-specific adjustments
  - Integration with librkisp_api
- **Required For**: OPTIONAL - Camera features only
- **Open Source Status**: **PARTIALLY OPEN**
  - Some components open source in rkaiq repository
  - Core algorithms and tuning data proprietary
- **Alternatives**:
  - Basic ISP control via V4L2
  - libcamera with custom tuning
- **Notes**:
  - Not needed for HDMI capture
  - Likely unused in KVM context

## Summary by Criticality

### CRITICAL (Required for Core Functionality)
1. **librockchip_mpp.so.0** - Video encoding (OPEN SOURCE)
   - Function: H.264 hardware encoding
   - Why: Essential for KVM video stream
   - Alternative: Software encoding (too slow for real-time)

### HIGH (Important for Performance)
2. **librga.so.2.1.0** - 2D graphics acceleration (OPEN SOURCE)
   - Function: Fast color conversion, scaling
   - Why: Enables low-latency video pipeline
   - Alternative: CPU-based conversion (higher latency, CPU usage)

3. **libeasymedia.so.1.0.1** - Media framework (OPEN SOURCE)
   - Function: Integration of MPP/RGA/ISP
   - Why: Simplifies media pipeline
   - Alternative: Direct MPP/RGA usage (more complex)

### MEDIUM (Quality Enhancement)
4. **libRKAP_3A.so** - Audio 3A processing (PROPRIETARY)
   - Function: Echo cancellation, noise reduction
   - Why: Improves audio quality
   - Alternative: WebRTC audio processing (open source)

5. **librkdb.so** - Vendor storage (PROPRIETARY)
   - Function: Device configuration, calibration
   - Why: Stores device-specific data
   - Alternative: Filesystem-based storage

### LOW (Optional Features)
6. **librkisp_api.so** - ISP API (PARTIALLY OPEN)
   - Function: Camera sensor control
   - Why: Not used for HDMI capture
   - Alternative: V4L2 ISP driver

7. **libRKAP_ANR.so** - Noise reduction (PROPRIETARY)
   - Function: Audio noise suppression
   - Why: Subset of RKAP_3A
   - Alternative: Same as RKAP_3A

8. **libRKAP_Common.so** - RKAP common (PROPRIETARY)
   - Function: Shared RKAP code
   - Why: Dependency of other RKAP libs
   - Alternative: Not applicable

9. **librkuvc.so** - UVC gadget (PARTIALLY OPEN)
   - Function: USB video output
   - Why: Optional feature for USB connection
   - Alternative: Direct UVC gadget driver

10. **librkaiq.so** - Auto Image Quality (PARTIALLY OPEN)
    - Function: Camera tuning
    - Why: Not used in KVM
    - Alternative: Not needed

11. **librockchip_vpu.so.0** - Legacy VPU (PARTIALLY OPEN)
    - Function: Old video API
    - Why: Backward compatibility only
    - Alternative: librockchip_mpp.so

## Open Source Alternatives Analysis

### Fully Replaceable with Open Source

| Proprietary Library | Open Source Alternative | Tradeoff |
|---------------------|-------------------------|----------|
| libRKAP_3A.so | WebRTC Audio Processing | Similar quality, well-maintained |
| libRKAP_ANR.so | Speex DSP, WebRTC APM | Slightly different algorithms |
| librkaiq.so | libcamera, V4L2 ISP | Not needed for HDMI capture |
| librkuvc.so | Linux UVC gadget driver | Direct kernel interface, more setup |

### Already Open Source (No Replacement Needed)

| Library | License | Repository |
|---------|---------|------------|
| librockchip_mpp.so | Apache 2.0 | github.com/rockchip-linux/mpp |
| librga.so | Apache 2.0 | github.com/airockchip/librga |
| libeasymedia.so | Apache 2.0 | github.com/rockchip-linux/rkmedia |

### No Viable Open Alternative (Critical)

| Proprietary Library | Reason No Alternative | Impact |
|---------------------|-----------------------|--------|
| librkdb.so | Vendor storage format proprietary | Can't access calibration data easily |

## Dependency Graph

```
uStreamer (video capture)
    |
    +-> libeasymedia.so (media framework)
            |
            +-> librockchip_mpp.so (video encoding) [CRITICAL]
            +-> librga.so (image conversion) [CRITICAL]
            +-> librkisp_api.so (ISP - optional)
                    |
                    +-> librkaiq.so (tuning - optional)

KVMD Audio
    |
    +-> libRKAP_3A.so (audio 3A)
            |
            +-> libRKAP_ANR.so (noise reduction)
            +-> libRKAP_Common.so (shared code)

Device Config
    |
    +-> librkdb.so (vendor storage)

Optional Features
    |
    +-> librkuvc.so (USB video out)
    +-> librockchip_vpu.so (legacy, unused)
```

## License Compliance

### Open Source Libraries (Apache 2.0)
- **librockchip_mpp.so.0** - Source available, Apache 2.0
- **librga.so.2.1.0** - Source available, Apache 2.0
- **libeasymedia.so.1.0.1** - Source available, Apache 2.0

**Compliance Status**: COMPLIANT
- Apache 2.0 allows binary distribution
- No source disclosure requirement (permissive license)
- Attribution required (should be in documentation)

### Proprietary Libraries
- **libRKAP_3A.so** - Rockchip proprietary
- **libRKAP_ANR.so** - Rockchip proprietary
- **libRKAP_Common.so** - Rockchip proprietary
- **librkdb.so** - Rockchip proprietary

**Compliance Status**: UNKNOWN
- Requires valid license from Rockchip
- GL.iNet likely has OEM/ODM license
- End-user redistribution may be restricted
- Check Rockchip SDK license agreement

### Partially Open Libraries
- **librkisp_api.so** - V4L2 driver open, library may be proprietary
- **librkaiq.so** - Some components open, core algorithms proprietary
- **librkuvc.so** - Kernel driver open, library wrapper status unclear

**Compliance Status**: VERIFY
- Check specific license for each component
- Some parts may have dual licensing

## Minimal System Requirements

### Absolute Minimum (Basic Video KVM)
1. **librockchip_mpp.so** - Video encoding (open source)
2. **librga.so** - Color conversion (open source)

With only these two libraries and software alternatives for other functions, basic KVM-over-IP operation is possible but with:
- Lower audio quality (no 3A processing)
- Software-based audio processing
- No vendor storage access
- No USB video output

### Recommended Minimum (Good User Experience)
1. **librockchip_mpp.so** - Video encoding
2. **librga.so** - Color conversion
3. **libeasymedia.so** - Media framework (simplifies integration)
4. **libRKAP_3A.so** - Audio 3A (better audio quality)
5. **librkdb.so** - Device configuration

### Full System (All Features)
- All libraries listed above
- Enables all hardware features
- Best performance and quality

## Recommendations

### For Users/Operators
1. **Understand Dependencies**: Core video functionality relies on open-source MPP and RGA
2. **Privacy**: RKAP audio libraries are proprietary black boxes - consider if acceptable
3. **Minimal Install**: If building custom firmware, only include critical libraries
4. **Open Alternatives**: Consider replacing RKAP with WebRTC APM for audio

### For GL.iNet (Vendor)
1. **License Clarity**: Document Rockchip library licenses in firmware
2. **Attribution**: Add Apache 2.0 attribution for MPP, RGA, easymedia
3. **Minimize Proprietary**: Use open WebRTC audio processing instead of RKAP
4. **Remove Unused**: Strip librkaiq, librkisp_api if not used for HDMI capture
5. **Source Availability**: Provide source for Apache 2.0 libraries (MPP, RGA) in SDK
6. **Vendor Lock-in**: Document dependency on librkdb for vendor storage

### For Open Source Community
1. **WebRTC Audio**: Integrate WebRTC APM as alternative to RKAP
2. **Vendor Storage**: Reverse engineer librkdb format for open alternative
3. **Mainline Support**: Continue work on V4L2 stateless video in mainline kernel
4. **Documentation**: Improve documentation for Rockchip media stack

## Security Considerations

### Proprietary Blob Risks
- **Closed Source**: Cannot audit for vulnerabilities or backdoors
- **Update Lag**: Dependent on Rockchip for security patches
- **Supply Chain**: Trust in Rockchip's development practices
- **Obfuscation**: Difficult to analyze behavior

### Mitigation Strategies
1. **Isolate**: Run in sandboxed environment if possible
2. **Monitor**: Use strace/ltrace to observe library behavior
3. **Minimize**: Only use truly required proprietary libraries
4. **Alternatives**: Prefer open source alternatives where viable
5. **Updates**: Keep Rockchip libraries updated to latest versions

### Specific Concerns
- **librkdb.so**: Accesses raw storage partition, potential for abuse
- **RKAP libraries**: Proprietary audio processing, unclear data handling
- **librkisp_api.so**: If not needed, should be removed to reduce attack surface

## References

### Open Source Repositories
- [Rockchip MPP](https://github.com/rockchip-linux/mpp) - Media Process Platform
- [Rockchip RGA](https://github.com/airockchip/librga) - 2D Graphics Acceleration
- [Rockchip RKMedia](https://github.com/rockchip-linux/rkmedia) - Easy Media Framework
- [Rockchip ISP Driver](https://opensource.rock-chips.com/wiki_Rockchip-isp1)

### Documentation
- [Rockchip Open Source Wiki](https://opensource.rock-chips.com/wiki_Main_Page)
- [Rockchip MPP Documentation](https://opensource.rock-chips.com/wiki_Mpp)
- [Rockchip RGA FAQ](https://github.com/airockchip/librga/blob/main/docs/Rockchip_FAQ_RGA_EN.md)
- [Collabora: RK3588 Open Source Boot Chain](https://www.collabora.com/news-and-blog/blog/2024/02/21/almost-a-fully-open-source-boot-chain-for-rockchips-rk3588/)

### Alternative Libraries
- [WebRTC Audio Processing Module](https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/)
- [Speex DSP](https://www.speex.org/)
- [libcamera](https://libcamera.org/)
- [V4L2 Codec Userspace API](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/dev-codec.html)

### Related Project Files
- [Shared Libraries List](packages.md)
- [Network Services Analysis](network-services.md)
- [GPL Binaries](gpl-binaries.md)
