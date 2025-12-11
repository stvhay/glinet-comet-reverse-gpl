# Device Tree Analysis

[← Analysis Reports](SUMMARY.md)

---

The firmware contains multiple DTBs for U-Boot and Linux, targeting the Rockchip RV1126 EVB DDR3 V13 board.

## Summary

| DTB | Size | Purpose |
|-----|------|---------|
| 0x1323B4 | 13 KB | U-Boot device tree |
| 0x49B9B4 | 97 KB | Linux kernel DTB |
| 0x28F1B4 | 2 KB | Bootloader FIT (Slot B) |

**Compatible:** `rockchip,rv1126-evb-ddr3-v13`

---

## Device Trees Found

## DTB #1: `system.dtb` (offset 0x1323B4)

- **Size:** 13660 bytes
- **Type:** U-Boot Device Tree
- **Model:** Rockchip RV1126 Evaluation Board
- **Compatible:** `rockchip,rv1126-evb`

## DTB #2: `system.dtb` (offset 0x1C597B4)

- **Size:** 110972 bytes
- **Type:** Device Tree
- **Model:** Rockchip RV1126 EVB DDR3 V13 Board
- **Compatible:** `rockchip,rv1126-evb-ddr3-v13`

## DTB #3: `system.dtb` (offset 0x28F1B4)

- **Size:** 1893 bytes
- **Type:** FIT Image (Flattened Image Tree)

### FIT Image Contents

```
	description = "FIT Image with ATF/OP-TEE/U-Boot/MCU";
			description = "U-Boot";
			type = "standalone";
			arch = "arm";
			os = "U-Boot";
			compression = "gzip";
			description = "OP-TEE";
			type = "firmware";
			arch = "arm";
			os = "op-tee";
			compression = "gzip";
			description = "U-Boot dtb";
			type = "flat_dt";
			arch = "arm";
			compression = "none";
			description = "rv1126-evb";
```

## DTB #4: `system.dtb` (offset 0x3323B4)

- **Size:** 13660 bytes
- **Type:** U-Boot Device Tree
- **Model:** Rockchip RV1126 Evaluation Board
- **Compatible:** `rockchip,rv1126-evb`

## DTB #5: `system.dtb` (offset 0x49B1B4)

- **Size:** 1411 bytes
- **Type:** FIT Image (Flattened Image Tree)

### FIT Image Contents

```
	description = "U-Boot FIT source file for arm";
			type = "flat_dt";
			arch = "arm";
			compression = "none";
			type = "kernel";
			arch = "arm";
			os = "linux";
			compression = "none";
			type = "multi";
			arch = "arm";
			compression = "none";
```

## DTB #6: `system.dtb` (offset 0x49B9B4)

- **Size:** 110972 bytes
- **Type:** Device Tree
- **Model:** Rockchip RV1126 EVB DDR3 V13 Board
- **Compatible:** `rockchip,rv1126-evb-ddr3-v13`

## DTB #7: `system.dtb` (offset 0x8F1B4)

- **Size:** 1893 bytes
- **Type:** FIT Image (Flattened Image Tree)

### FIT Image Contents

```
	description = "FIT Image with ATF/OP-TEE/U-Boot/MCU";
			description = "U-Boot";
			type = "standalone";
			arch = "arm";
			os = "U-Boot";
			compression = "gzip";
			description = "OP-TEE";
			type = "firmware";
			arch = "arm";
			os = "op-tee";
			compression = "gzip";
			description = "U-Boot dtb";
			type = "flat_dt";
			arch = "arm";
			compression = "none";
			description = "rv1126-evb";
```

## DTB #8: `system.dtb` (offset 0xC385B4)

- **Size:** 110972 bytes
- **Type:** Device Tree
- **Model:** Rockchip RV1126 EVB DDR3 V13 Board
- **Compatible:** `rockchip,rv1126-evb-ddr3-v13`

## DTB #9: `system.dtb` (offset 0xCC91B4)

- **Size:** 1767 bytes
- **Type:** FIT Image (Flattened Image Tree)

### FIT Image Contents

```
	description = "U-Boot FIT source file for arm";
			type = "flat_dt";
			arch = "arm";
			compression = "none";
			type = "kernel";
			arch = "arm";
			os = "linux";
			compression = "none";
			type = "ramdisk";
			arch = "arm";
			os = "linux";
			compression = "none";
			type = "multi";
			arch = "arm";
			compression = "none";
```

## DTB #10: `system.dtb` (offset 0xCC99B4)

- **Size:** 110972 bytes
- **Type:** Device Tree
- **Model:** Rockchip RV1126 EVB DDR3 V13 Board
- **Compatible:** `rockchip,rv1126-evb-ddr3-v13`

---

**Total Device Trees found:** 10
