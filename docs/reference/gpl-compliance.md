# GPL Compliance Reference

Reference information for GPL compliance in embedded Linux systems.

## Common GPL Components

| Component | License | Obligation |
|-----------|---------|------------|
| Linux Kernel | GPL-2.0 | Must provide source code |
| U-Boot | GPL-2.0+ | Must provide source code |
| BusyBox | GPL-2.0 | Must provide source code |
| glibc | LGPL-2.1 | Must provide source if modified |
| GCC runtime | GPL-3.0 with exception | Typically no obligation |

## LGPL Components

| Component | License | Obligation |
|-----------|---------|------------|
| glibc | LGPL-2.1 | Source if modified; allow relinking |
| FFmpeg (some) | LGPL-2.1+ | Source if modified |

## GPL Compliance Requirements

### For GPL-2.0 Components:
1. Provide complete corresponding source code
2. Include copy of GPL-2.0 license
3. Preserve copyright notices
4. Provide written offer valid for 3 years (or distribute source with binary)

### For LGPL-2.1 Components:
1. Provide source code if modified
2. Allow user to relink with modified library
3. Include copy of LGPL-2.1 license

## References

- [GPL-2.0 Full Text](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
- [LGPL-2.1 Full Text](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
- [Software Freedom Conservancy Compliance Guide](https://copyleft.org/guide/)
