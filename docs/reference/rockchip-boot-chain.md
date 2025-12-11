# Rockchip RV1126 Boot Chain

Standard boot chain for Rockchip RV1126 SoC devices.

## Boot Sequence

```
┌─────────────┐
│  Power On   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  BootROM    │  Rockchip mask ROM (fixed in silicon)
│  (BROM)     │  - Initializes basic hardware
└──────┬──────┘  - Loads SPL from eMMC/SD
       │
       ▼
┌─────────────┐
│  SPL/TPL    │  Secondary Program Loader
│             │  - DDR memory initialization
└──────┬──────┘  - Loads U-Boot FIT image
       │
       ▼
┌─────────────┐
│  OP-TEE     │  Trusted Execution Environment
│  (tee.bin)  │  - Secure world initialization
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  U-Boot     │  - Hardware initialization
│             │  - Loads kernel FIT image
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Linux      │  - Main operating system
│  Kernel     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Initramfs  │  - Early userspace init
│             │  - Mounts SquashFS root
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  SquashFS   │  Main root filesystem
│  Rootfs     │  - Read-only
└─────────────┘
```

## Components

| Stage | Component | Purpose |
|-------|-----------|---------|
| 1 | BootROM | Fixed in silicon, initializes clocks and loads SPL |
| 2 | SPL/TPL | DDR initialization, loads main bootloader |
| 3 | OP-TEE | Trusted Execution Environment for secure operations |
| 4 | U-Boot | Full bootloader, loads and verifies kernel |
| 5 | Kernel | Linux kernel with device tree |
| 6 | Initramfs | Early userspace, mounts root filesystem |
| 7 | Rootfs | Main filesystem (SquashFS for embedded devices) |

## References

- [Rockchip Wiki - Boot Flow](https://opensource.rock-chips.com/wiki_Boot_option)
- [U-Boot FIT Image Documentation](https://u-boot.readthedocs.io/en/latest/usage/fit/index.html)
