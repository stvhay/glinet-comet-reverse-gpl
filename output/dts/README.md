# GL.iNet Comet (RM1) Derivative Device Tree

This directory contains a reverse-engineered derivative device tree for the GL.iNet Comet (RM1) KVM.

## Files

- **rv1126-glinet-rm1.dts** - Derivative DTS that properly includes upstream Rockchip sources
- **upstream/** - Reference .dtsi files from Firefly kernel (auto-downloaded by test script)

## What is this?

The GL.iNet Comet firmware contains a device tree blob (DTB) that is derived from Rockchip's GPL-licensed RV1126 EVB DDR3 V13 reference board design.

This derivative DTS file:
1. Uses proper `#include` statements to reference upstream GPL-licensed .dtsi files
2. Contains only the GL.iNet-specific customizations (minimal diff)
3. Compiles to a DTB that is semantically equivalent to the original firmware DTB
4. Documents the reverse engineering methodology in comments
5. Properly attributes copyright and license (GPL-2.0+ / MIT)

## GL.iNet Customizations

Analysis shows GL.iNet made minimal modifications to the reference design:

### 1. Modified bootargs
Added `rootfstype=squashfs` to boot arguments (reference uses ext4)

### 2. Added gl_hw node
Product-specific hardware information node containing:
- Model identifier: "rm1"
- Hardware patch identifiers (hdmipatch)
- USB product ID configuration
- WAN interface designation
- Flash size (8GB eMMC)
- Factory data partition layout with offsets for:
  - MAC address
  - DDNS credentials
  - Serial numbers
  - Device tokens (multiple types)
  - Device certificates

## Validation

Run the test script to verify the derivative DTS is correct:

```bash
# Quick semantic validation (fast, no download)
./scripts/test-derivative-dts.sh

# Full compilation test (downloads ~500MB kernel source)
FULL_COMPILE=true ./scripts/test-derivative-dts.sh
```

The test validates:
- ✓ Derivative DTS structure is correct
- ✓ GPL license and methodology are documented
- ✓ Upstream includes are properly referenced
- ✓ GL.iNet customizations are accurately documented
- ✓ bootargs match original firmware exactly
- ✓ gl_hw node structure is complete (19/19 properties)
- ✓ (Optional) Full compilation with kernel source tree succeeds

## Reference Sources

The upstream Rockchip device tree sources are GPL-2.0+ licensed and available at:

- Repository: https://gitlab.com/firefly-linux/kernel
- Branch: rv1126_rv1109/linux_release_v2.2.5g
- Files:
  - arch/arm/boot/dts/rv1126.dtsi
  - arch/arm/boot/dts/rv1126-evb-v13.dtsi
  - arch/arm/boot/dts/rv1126-evb-v12.dtsi
  - arch/arm/boot/dts/rv1126-evb-v10.dtsi
  - arch/arm/boot/dts/rv1126-dram-default-timing.dtsi
  - arch/arm/boot/dts/rv1126-evb-ddr3-v13.dts (reference board)

## GPL Compliance Implications

This derivative work demonstrates that:

1. GL.iNet's device tree is based on GPL-licensed Rockchip sources
2. The customization level is minimal (2 changes: bootargs + gl_hw node)
3. GL.iNet maintains hardware compatibility via correct compatible strings
4. The device tree qualifies as a GPL derivative work under Linux kernel license

## Methodology

This derivative DTS was created using black-box reverse engineering:

1. Extracted DTB from firmware using binwalk + FIT image analysis
2. Decompiled DTB to DTS using `dtc -I dtb -O dts`
3. Downloaded reference Rockchip DTS from public GPL repository
4. Performed diff analysis to identify GL.iNet customizations
5. Created derivative DTS using upstream includes + documented deltas
6. Validated compilation and semantic equivalence

All findings are reproducible by running the scripts in this repository.
