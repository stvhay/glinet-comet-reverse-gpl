# Device Tree Analysis

Analysis of GL.iNet Comet (RM1) device tree compared to reference Rockchip EVB design.

## Derivative Device Tree

We have created a clean-room reverse engineered derivative device tree source file:

**[rv1126-glinet-rm1.dts](../output/dts/rv1126-glinet-rm1.dts)** - GPL-2.0+/MIT licensed derivative DTS

This derivative DTS:
- Uses proper `#include` statements to reference upstream Rockchip GPL sources
- Documents only the GL.iNet-specific customizations
- Compiles to a DTB semantically equivalent to the firmware's original DTB
- Includes full methodology documentation in comments

## Key Findings

### Device Identification

- **Model**: GL.iNet Comet (RM1)
- **Compatible**: `glinet,rm1`, `rockchip,rv1126-evb-ddr3-v13`, `rockchip,rv1126`
- **Reference Board**: Rockchip RV1126 EVB DDR3 V13

### GL.iNet Customizations

Analysis shows **minimal customization** from the reference design:

1. **Modified bootargs**: Added `rootfstype=squashfs` (reference uses ext4)
2. **Added gl_hw node**: Product-specific hardware information including:
   - Model identifier: "rm1"
   - Hardware patches (hdmipatch)
   - USB PID configuration
   - WAN interface designation
   - Flash size (8GB eMMC)
   - Factory data partition layout with offsets for MAC, serial numbers, tokens, and certificates

## GPL Compliance Implications

The GL.iNet firmware's device tree is a **derivative work** of GPL-licensed Rockchip sources:

- Device tree uses GPL-2.0+ licensed Rockchip sources
- GL.iNet customized the model name but maintains hardware compatibility with reference EVB
- This indicates derivative work with minimal changes
- GL.iNet should provide source code for their device tree modifications per GPL requirements

## Reference Sources

The reference Rockchip device tree sources (GPL-2.0+ licensed) are available at:

- Repository: https://gitlab.com/firefly-linux/kernel
- Branch: `rv1126_rv1109/linux_release_v2.2.5g`
- Files:
  - [rv1126.dtsi](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126.dtsi)
  - [rv1126-evb-v13.dtsi](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126-evb-v13.dtsi)
  - [rv1126-evb-ddr3-v13.dts](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126-evb-ddr3-v13.dts) (reference board)

## Validation

Our derivative DTS has been validated with comprehensive tests:

**Test script**: [scripts/test-derivative-dts.sh](../scripts/test-derivative-dts.sh)

### Quick Semantic Test
```bash
./scripts/test-derivative-dts.sh
```
- Validates structure, GPL license, methodology ✅
- Compares bootargs with original firmware ✅
- Validates gl_hw node (19/19 properties match) ✅

### Full Compilation Test
```bash
FULL_COMPILE=true ./scripts/test-derivative-dts.sh
```
- Clones Firefly kernel source
- Preprocesses DTS with cpp (handles #include directives)
- Compiles to 81K DTB ✅
- All GL.iNet customizations present in compiled output ✅

## Methodology

This analysis was performed using black-box reverse engineering:

1. Extracted device tree blob (DTB) from firmware using binwalk + FIT image analysis
2. Decompiled DTB to DTS using `dtc -I dtb -O dts`
3. Downloaded reference Rockchip DTS from public GPL repository
4. Performed diff analysis to identify GL.iNet customizations
5. Created derivative DTS using upstream includes + documented deltas
6. Validated compilation and semantic equivalence

All findings are **traceable to automated scripts** - see:
- [scripts/analyze_device_tree_diff.sh](../scripts/analyze_device_tree_diff.sh) - Device tree comparison analysis
- [scripts/dump-device-trees.sh](../scripts/dump-device-trees.sh) - DTB extraction from firmware

## Documentation

Complete documentation available at: [output/dts/README.md](../output/dts/README.md)

---

**Related**: See [Issue #26](https://github.com/stvhay/glinet-comet-reverse-gpl/issues/26) for full analysis details.
