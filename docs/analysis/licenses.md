# Automated License Detection

Automated analysis of licenses in GL.iNet Comet firmware.

Generated: 2025-12-11T06:21:51Z

## License Detection Methods

1. **Binary string extraction** - Search for license text in executables
2. **Python package metadata** - Parse `*.dist-info/METADATA` files
3. **License file analysis** - Identify license type from COPYING/LICENSE files
4. **Known library lookup** - Cross-reference against known open source licenses

## Binary License Strings

License information extracted from executable binaries:

| Binary | License String | Detected License |
|--------|----------------|------------------|
| `busybox` | Licensed under GPLv2. See source distribution for detailed... | GPL-2.0 |
| `coreutils` | License GPLv3+: GNU GPL version 3 or later <https://gnu.org/... | GPL-3.0 |
| `gdb` |                     GNU GENERAL PUBLIC LICENSE... | Unknown |

## Python Package Licenses

Licenses from Python package metadata (`*.dist-info/METADATA`):

| Package | Version | License |
|---------|---------|---------|
| *No Python packages found* | - | - |

## License File Analysis

License types identified from LICENSE/COPYING file contents:

| File | Detected License | Category |
|------|------------------|----------|
| `/usr/lib/python3.12/site-packages/shellingham-1.5.4.dist-info/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/async_lru-2.0.4.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/scikit_build_core-0.10.7.dist-info/licenses/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/pexpect-4.9.0.dist-info/LICENSE` | ISC | Permissive |
| `/usr/lib/python3.12/site-packages/scikit_build_core/_vendor/pyproject_metadata/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/netifaces-0.11.0.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/python_periphery-2.4.1.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/zstandard-0.23.0.dist-info/LICENSE` | BSD | Permissive |
| `/usr/lib/python3.12/site-packages/jaraco.classes-3.4.0.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/pyusb-1.2.1.dist-info/LICENSE` | BSD | Permissive |
| `/usr/lib/python3.12/site-packages/multidict-6.1.0.dist-info/LICENSE` | Apache-2.0 | Permissive |
| `/usr/lib/python3.12/site-packages/ptyprocess-0.7.0.dist-info/LICENSE` | ISC | Permissive |
| `/usr/lib/python3.12/site-packages/aiosignal-1.3.1.dist-info/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/rapidfuzz-3.10.0.dist-info/licenses/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/crashtest-0.4.1.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/pygments-2.17.2.dist-info/licenses/LICENSE` | BSD | Permissive |
| `/usr/lib/python3.12/site-packages/spidev-3.6.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/psutil-5.9.7.dist-info/LICENSE` | BSD-3-Clause | Permissive |
| `/usr/lib/python3.12/site-packages/msgpack-1.1.0.dist-info/COPYING` | Apache-2.0 | Permissive |
| `/usr/lib/python3.12/site-packages/kvmd-4.82.dist-info/LICENSE` | GPL-3.0 | Copyleft |
| `/usr/lib/python3.12/site-packages/pillow-10.3.0.dist-info/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/requests-2.32.3.dist-info/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/asyncinotify-4.2.1.dist-info/LICENSE` | GPL-3.0 | Copyleft |
| `/usr/lib/python3.12/site-packages/tomlkit-0.13.2.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/python_dateutil-2.6.0.dist-info/LICENSE` | BSD | Permissive |
| `/usr/lib/python3.12/site-packages/aiohttp-3.10.5.dist-info/LICENSE.txt` | Apache-2.0 | Permissive |
| `/usr/lib/python3.12/site-packages/six-1.16.0.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/aiohappyeyeballs-2.4.0.dist-info/LICENSE` | Unknown | Unknown |
| `/usr/lib/python3.12/site-packages/pycares-4.4.0.dist-info/LICENSE` | MIT | Permissive |
| `/usr/lib/python3.12/site-packages/pyserial_asyncio-0.6.dist-info/LICENSE.txt` | BSD-3-Clause | Permissive |

## Shared Library Licenses

Licenses for shared libraries (from known database):

| Library | License | Category | Source Disclosure |
|---------|---------|----------|-------------------|
| `libjson-c.so.3.0.1` | MIT | Permissive | No |
| `libpcrecpp.so.0.0.1` | BSD-3-Clause | Permissive | No |
| `libevent_pthreads-2.1.so.7.0.1` | BSD-3-Clause | Permissive | No |
| `libnl-3.so.200.26.0` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libboost_chrono.so.1.66.0` | BSL-1.0 | Permissive | No |
| `libgio-2.0.so.0.6400.4` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libspeexdsp.so.1.5.0` | BSD-3-Clause | Permissive | No |
| `libnl-nf-3.so.200.26.0` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libnl-genl-3.so.200.26.0` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libogg.so.0.8.3` | BSD-3-Clause | Permissive | No |
| `libgnutls-openssl.so.27.0.2` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libpython3.so` | PSF-2.0 | Unknown | No |
| `libevent_openssl-2.1.so.7.0.1` | BSD-3-Clause | Permissive | No |
| `libjansson.so.4.10.0` | MIT | Permissive | No |
| `libavdevice.so.58.5.100` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libboost_unit_test_framework.so.1.66.0` | BSL-1.0 | Permissive | No |
| `libavcodec.so.58.35.100` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libgobject-2.0.so.0.6400.4` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libdrm_rockchip.so.1.0.0` | MIT | Permissive | No |
| `libncurses.so.6.0` | MIT | Permissive | No |
| `libavutil.so.56.22.100` | LGPL-2.1 | Copyleft | Yes (library only) |
| `librga.so.2.1.0` | Apache-2.0 | Permissive | No |
| `libbluetooth.so.3.18.16` | GPL-2.0 | Copyleft | Yes (full) |
| `libswresample.so.3.3.100` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libeasymedia.so.1.0.1` | Apache-2.0 | Permissive | No |
| `libcrypto.so.1.1` | OpenSSL | Permissive | No |
| `libmad.so.0.2.1` | GPL-2.0 | Copyleft | Yes (full) |
| `libopus.so.0.8.0` | BSD-3-Clause | Permissive | No |
| `libpng16.so.16.37.0` | Zlib | Permissive | No |
| `libboost_system.so.1.66.0` | BSL-1.0 | Permissive | No |
| `libglib-2.0.so.0.6400.4` | LGPL-2.1 | Copyleft | Yes (library only) |
| `libstdc++.so.6.0.25-gdb.py` | GPL-3.0-with-GCC-exception | Unknown | No |
| `libgcc_s.so.1` | GPL-3.0-with-GCC-exception | Unknown | No |
| `libpcreposix.so.0.0.5` | BSD-3-Clause | Permissive | No |

## Summary

### Components Requiring Source Disclosure

The following components are under copyleft licenses and require source code disclosure:

- File: /usr/lib/python3.12/site-packages/asyncinotify-4.2.1.dist-info/LICENSE (GPL-3.0)
- File: /usr/lib/python3.12/site-packages/kvmd-4.82.dist-info/LICENSE (GPL-3.0)
- Library: libavcodec.so.58.35.100 (LGPL-2.1)
- Library: libavdevice.so.58.5.100 (LGPL-2.1)
- Library: libavutil.so.56.22.100 (LGPL-2.1)
- Library: libbluetooth.so.3.18.16 (GPL-2.0)
- Library: libgio-2.0.so.0.6400.4 (LGPL-2.1)
- Library: libglib-2.0.so.0.6400.4 (LGPL-2.1)
- Library: libgnutls-openssl.so.27.0.2 (LGPL-2.1)
- Library: libgobject-2.0.so.0.6400.4 (LGPL-2.1)
- Library: libmad.so.0.2.1 (GPL-2.0)
- Library: libnl-3.so.200.26.0 (LGPL-2.1)
- Library: libnl-genl-3.so.200.26.0 (LGPL-2.1)
- Library: libnl-nf-3.so.200.26.0 (LGPL-2.1)
- Library: libswresample.so.3.3.100 (LGPL-2.1)

### License Category Counts

| Category | Count |
|----------|-------|
| Copyleft (GPL, LGPL, MPL) | 15 |
| Permissive (MIT, BSD, Apache) | 18 |

### Source Disclosure Requirements

| License | Disclosure Scope |
|---------|------------------|
| GPL-2.0, GPL-3.0 | Complete source for derivative work |
| LGPL-2.1, LGPL-3.0 | Library source + re-linking capability |
| MPL-2.0 | Modified files only |
| MIT, BSD, Apache-2.0 | None (permissive) |

---

*Note: This is automated detection and may not be comprehensive. Manual verification recommended for legal compliance.*
