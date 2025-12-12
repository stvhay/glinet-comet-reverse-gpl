
# Device Tree Analysis

Analysis of GL.iNet Comet (RM1) device tree compared to reference Rockchip EVB design.

## Device Identification

The kernel device tree identifies the hardware as:

- **Model**: rm1[^1]
- **Compatible**: rockchip,rv1126-evb-ddr3-v13[^2]
- **Reference Board**: Rockchip RV1126 EVB DDR3 V13[^3]

## Customization Level

Minimal customization from reference design.

## Analysis

The GL.iNet firmware's device tree shows:
- Model name changed to "rm1" (product-specific identifier)
- Compatible string maintained as "rockchip,rv1126-evb-ddr3-v13" (hardware compatibility identifier)
- This indicates GL.iNet is using the Rockchip RV1126 EVB DDR3 V13 hardware design with minimal modifications

## GPL Compliance Implications

Device tree uses GPL-2.0+ licensed Rockchip sources. GL.iNet customized model name but maintains hardware compatibility with reference EVB, indicating derivative work with minimal changes.

## Reference Sources

The reference Rockchip device tree sources are available at:

- [rv1126-evb-ddr3-v13.dts](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126-evb-ddr3-v13.dts)
- [rv1126.dtsi](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126.dtsi)
- [rv1126-evb-v13.dtsi](https://gitlab.com/firefly-linux/kernel/-/blob/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126-evb-v13.dtsi)

These files are licensed under GPL-2.0+ or MIT, as documented in their SPDX headers.

## Methodology

This analysis was performed by:
1. Extracting device tree blob (DTB) from firmware
2. Decompiling DTB to device tree source (DTS) using `dtc`
3. Comparing with reference Rockchip EVB DTS from Firefly kernel repository
4. Identifying customizations via diff analysis

---


## Sources

[^1]: [scripts/analyze_device_tree_diff.sh](../scripts/analyze_device_tree_diff.sh) - `grep 'model = ' output/dtb/kernel-fit.dts | awk -F'"' '{print $2}'`
[^2]: [scripts/analyze_device_tree_diff.sh](../scripts/analyze_device_tree_diff.sh) - `grep 'compatible = ' output/dtb/kernel-fit.dts | awk -F'"' '{print $2}'`
[^3]: [scripts/analyze_device_tree_diff.sh](../scripts/analyze_device_tree_diff.sh) - `curl -s https://gitlab.com/firefly-linux/kernel/-/raw/rv1126_rv1109/linux_release_v2.2.5g/arch/arm/boot/dts/rv1126-evb-ddr3-v13.dts | grep 'model = '`