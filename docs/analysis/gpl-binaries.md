# GPL-Licensed Binaries

[← Analysis Reports](SUMMARY.md)

---

The firmware contains BusyBox, GNU Coreutils, and several other GPL-licensed tools that require source code disclosure.

## BusyBox

| Property | Value |
|----------|-------|
| Version | 1.27.2 |
| Build Date | 2025-11-27 08:14:38 UTC |
| Location | /bin/busybox |
| Size | 895,608 bytes |
| License | GPL-2.0 |

BusyBox provides most shell utilities as a single binary with symlinks.

## GNU Coreutils

| Property | Value |
|----------|-------|
| Location | /usr/bin/coreutils |
| Size | 1,050,516 bytes |
| License | GPL-3.0+ |

## Other GPL Tools

| Tool | License | Found |
|------|---------|-------|
| bash | GPL-3.0+ | Yes |
| gzip | GPL-3.0+ | Yes |
| tar | GPL-3.0+ | Yes |
| grep | GPL-3.0+ | Yes |
| sed | GPL-3.0+ | Yes |
| awk | GPL-3.0+ | Yes |
| vim | Vim (GPL-compatible) | Yes |

## GPL Compliance

For each GPL-licensed binary, GL.iNet must provide:

- Source code (or reference to exact upstream version)
- Build configuration
- Any patches applied
- Build instructions

## See Also

- [Automated License Detection](licenses.md)
- [GPL Compliance Analysis](../GPL-COMPLIANCE-ANALYSIS.md)
