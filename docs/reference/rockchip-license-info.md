# Rockchip Component Licensing

[← Analysis Reports](../analysis/SUMMARY.md)

---

Reference information about licensing of common Rockchip components.

## Proprietary Libraries

### Media Processing Platform (MPP)
- **Libraries**: `librockchip_mpp.so`, `libmpp.so`, `librk_mpi.so`
- **License**: Proprietary (Rockchip)
- **Notes**: Apache-2.0 headers for API only, binary blob is proprietary

### Rockchip Graphics Acceleration (RGA)
- **Libraries**: `librga.so`, `librockchip_rga.so`
- **License**: Proprietary (Rockchip)
- **Notes**: 2D graphics acceleration, closed source

### Image Signal Processor (ISP)
- **Libraries**: `librkaiq.so`, `librkisp.so`, `librk_aiq.so`
- **License**: Proprietary (Rockchip)
- **Notes**: Camera ISP processing, closed source

### Neural Processing Unit (NPU)
- **Libraries**: `librknn_runtime.so`, `librknnrt.so`
- **License**: Proprietary (Rockchip)
- **Notes**: AI/ML inference acceleration

## Firmware Blobs

- **Location**: `/lib/firmware/`
- **License**: Typically redistributable but not open source
- **Notes**: WiFi, Bluetooth, and other peripheral firmware

## Kernel Modules

- **Requirement**: Must be GPL-compatible if statically linked with kernel
- **Exception**: Proprietary modules may use module tainting
- **Notes**: Check `MODULE_LICENSE()` macro in source or strings in binary

## GPL Compliance Implications

1. **Rockchip libraries**: Not required to release source (proprietary)
2. **Firmware blobs**: Check individual firmware licenses
3. **Kernel modules**: GPL-tainted modules have reduced functionality

## References

- [Rockchip Open Source](https://opensource.rock-chips.com/)
- [Linux Kernel Module Licensing](https://www.kernel.org/doc/html/latest/process/license-rules.html)
