# Firmware Structure (Binwalk)

[← Analysis Reports](SUMMARY.md)

---

The firmware contains two sets of bootloader FIT images (A/B redundancy), a kernel FIT, initramfs, SquashFS root filesystem, and two EXT4 data partitions.

## Firmware Layout

| Offset | Type | Description |
|--------|------|-------------|
| 0x8F1B4 | FIT | Bootloader FIT (U-Boot + OP-TEE) - Slot A |
| 0x28F1B4 | FIT | Bootloader FIT - Slot B (duplicate) |
| 0x49B9B4 | FIT | Kernel FIT (kernel + DTB) |
| 0x1465DB4 | gzip | Initramfs (rootfs.cpio, 8.3 MB) |
| 0x1CEA1B4 | SquashFS | Root filesystem (231 MB) |
| 0xF9E01B4 | EXT4 | OEM partition (6 MB) |
| 0xFFE01B4 | EXT4 | Userdata partition (5 MB) |

## Raw Binwalk Output

```
DECIMAL       HEX           DESCRIPTION
------------------------------------------------------------------------
586164        0x8F1B4       Device tree blob (DTB), FIT image
590260        0x901B4       gzip: u-boot-nodtb.bin (447 KB)
1037748       0xFD5B4       gzip: tee.bin (216 KB)
1254324       0x1323B4      Device tree blob (DTB), 11 KB
2683316       0x28F1B4      Device tree blob (DTB), FIT image [Slot B]
2687412       0x2901B4      gzip: u-boot-nodtb.bin [duplicate]
3134900       0x2FD5B4      gzip: tee.bin [duplicate]
4829620       0x49B1B4      Device tree blob (DTB)
4831668       0x49B9B4      Device tree blob (DTB), 96 KB
21388724      0x1465DB4     gzip: rootfs.cpio (8.3 MB)
30319028      0x1CEA1B4     SquashFS v4.0, gzip, 231 MB
262013364     0xF9E01B4     EXT4 filesystem, 6 MB
268304820     0xFFE01B4     EXT4 filesystem, 5 MB
```

## Key Observations

1. **A/B Redundancy**: Bootloader FIT images appear twice (slots A and B)
2. **Signed Boot**: FIT images use sha256,rsa2048 signatures
3. **Compressed Root**: SquashFS with gzip compression
4. **Initramfs**: Separate CPIO archive for early boot

## See Also

- [Boot Process](boot-process.md) — Partition layout and boot chain
- [Device Trees](device-trees.md) — DTB analysis
