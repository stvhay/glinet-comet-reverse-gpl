# Network Services & Attack Surface

[← Analysis Reports](SUMMARY.md)

---

The Comet exposes HTTPS (443), SSH (22), and WebRTC services. The web API requires authentication except for the one-time initialization endpoint.

**Platform:** Rockchip RV1126, Buildroot 2018.02-rc3, PiKVM-based
**Firmware:** V1.7.2

## Key Attack Surface

| Service | Port | Auth Required | Risk |
|---------|------|---------------|------|
| KVMD API | 443/tcp | Yes (except init) | Medium |
| SSH | 22/tcp | Yes | Medium |
| Janus WebRTC | 8088/tcp | Via KVMD | Medium |
| VNC | 5900/tcp | Yes (if enabled) | High |
| mDNS | 5353/udp | No | Low |

**Notable findings:**
- `/api/init/init` endpoint is unauthenticated on unconfigured devices
- Debug tools (GDB, valgrind) present in production firmware
- Buildroot 2018.02-rc3 may have outdated packages with known CVEs

---

## Detailed Analysis

## Network Services Inventory

### Primary Services

#### 1. KVMD (KVM Daemon) - Web Interface & API
- **Service**: kvmd (Python-based)
- **Binary**: `/usr/bin/kvmd`
- **Type**: Python script
- **Primary Ports**:
  - **443/tcp** - HTTPS (nginx reverse proxy)
  - **80/tcp** - HTTP (redirects to HTTPS)
- **Configuration**: `/etc/kvmd/`
- **Purpose**: Main KVM control interface and API server

**API Endpoints** (Based on PiKVM architecture):
- `/api/auth/check` - Authentication verification
- `/api/info` - Device information
- `/api/log` - System logs
- `/api/ws` - WebSocket for real-time events
- `/api/hid` - Keyboard/mouse control
- `/api/atx` - Power control
- `/api/msd` - Mass storage device emulation
- `/api/streamer` - Video stream control
- `/api/export` - Configuration export
- `/api/init/init?password=[val]` - First-time device initialization (GL.iNet specific)
- `/api/init/is_inited` - Check if device is initialized (returns country code)

#### 2. Nginx - Web Server
- **Service**: nginx
- **Configuration**: `/etc/kvmd/nginx-kvmd.conf`
- **Port**: 443/tcp (HTTPS), 80/tcp (HTTP)
- **Purpose**: Reverse proxy for KVMD, serves web UI
- **Libraries**: libssl.so.1.1, libcrypto.so.1.1

#### 3. Janus Gateway - WebRTC
- **Service**: Janus WebRTC gateway
- **Version**: 2.0.6 (GPL-3.0)
- **Configuration**: Custom plugins in `/usr/lib/janus/`
- **Libraries**:
  - `libjanus_gelfevh.so.2.0.6` - Event handler
  - `libjanus_wsevh.so.2.0.6` - WebSocket event handler
  - `libjanus_nosip.so.2.0.6` - NoSIP plugin
  - `libjanus_http.so.2.0.6` - HTTP transport
  - `libjanus_pfunix.so.2.0.6` - Unix socket transport
  - `libjanus_websockets.so.2.0.6` - WebSocket transport
- **Purpose**: Real-time video/audio streaming via WebRTC
- **Likely Port**: 8088/tcp (HTTP), 8089/tcp (HTTPS), 8188/tcp (WebSocket)

#### 4. uStreamer - Video Capture & Streaming
- **Binary**: `/usr/bin/ustreamer-dump`
- **Type**: Native binary (ARM)
- **Purpose**: H.264 video capture and encoding for KVM video stream
- **Integration**: Works with Janus for WebRTC delivery

#### 5. VNC Server
- **Service**: kvmd-vnc
- **Binary**: `/usr/bin/kvmd-vnc`
- **Type**: Python script
- **Default Port**: 5900/tcp (VNC)
- **Purpose**: VNC protocol access to KVM console
- **Authentication**: VNCAuth (typically disabled by default in PiKVM)

#### 6. Live555 RTSP Server
- **Binary**: `/usr/bin/live555MediaServer`
- **Library**: libUsageEnvironment.so, libBasicUsageEnvironment.so, libliveMedia.so, libgroupsock.so
- **Default Port**: 554/tcp (RTSP), 8554/tcp (alternative)
- **Purpose**: RTSP streaming for video feeds
- **Status**: May be used as alternative to WebRTC

### Network Management Services

#### 7. SSH Server
- **Service**: OpenSSH/Dropbear (typical for Buildroot)
- **Default Port**: 22/tcp
- **User**: root
- **Authentication**: Password-based (same as web admin password)
- **Status**: Enabled by default

#### 8. mDNS Responder
- **Binary**: `/usr/bin/mDNSResponder`
- **Script**: `/usr/bin/gl_mdns`
- **Port**: 5353/udp (mDNS)
- **Purpose**: Service discovery, advertises `glkvm.local` hostname
- **Protocol**: Multicast DNS (Bonjour/Avahi compatible)

#### 9. ZeroTier VPN
- **Binary**: `/usr/bin/zerotier-one`
- **Default Port**: 9993/udp
- **Purpose**: Optional VPN for remote access
- **Status**: User-configurable, not enabled by default

### Auxiliary Services

#### 10. SNMP Agent
- **Libraries**:
  - `libnetsnmp.so.40.2.0`
  - `libnetsnmpagent.so.40.2.0`
  - `libnetsnmphelpers.so.40.2.0`
  - `libnetsnmpmibs.so.40.2.0`
  - `libnetsnmptrapd.so.40.2.0`
- **Binaries**: snmpset, snmptranslate, snmpdelta, snmpdf
- **Ports**: 161/udp (SNMP), 162/udp (SNMP traps)
- **Status**: Libraries present, likely disabled by default

#### 11. Bluetooth Services
- **Library**: `libbluetooth.so.3.18.16`
- **Binary**: `/usr/bin/bluetoothctl`
- **Plugin**: `/usr/lib/bluetooth/plugins/sixaxis.so`
- **Purpose**: Bluetooth peripheral support (keyboards, mice)
- **Status**: Optional, hardware-dependent

#### 12. D-Bus Message Bus
- **Libraries**:
  - `libdbus-1.so.3.19.4`
  - `libdbus-glib-1.so.2.3.3`
  - `libdbus-c++-1.so.0.0.0`
- **Binaries**: dbus-monitor, dbus-binding-tool
- **Socket**: Unix domain socket
- **Purpose**: Inter-process communication

#### 13. STUN Client
- **Binary**: `/usr/bin/stund`
- **Purpose**: NAT traversal for WebRTC
- **External Ports**: 3478/udp (STUN), 3479/udp
- **Direction**: Outbound connections to STUN servers

#### 14. iPerf3 Server
- **Library**: `libiperf.so.0.0.0`
- **Port**: 5201/tcp (default)
- **Purpose**: Network performance testing
- **Status**: Tool available, server likely disabled

### Cloud/Remote Access Services

#### 15. GL.iNet Cloud Service
- **Binary**: `/usr/bin/gl-cloud` (Lua bytecode)
- **Purpose**: GL.iNet proprietary cloud access ("AstroWarp")
- **Protocol**: HTTPS outbound
- **Features**: Remote access without VPN/port forwarding
- **Privacy**: Phones home to GL.iNet servers

#### 16. Tailscale VPN Integration
- **Status**: Supported (documentation mentions integration)
- **Purpose**: Alternative VPN for remote access
- **Configuration**: Via web interface

## Web Server & API Details

### Nginx Configuration
- **Config Location**: `/etc/kvmd/nginx-kvmd.conf`
- **SSL/TLS**: Self-signed certificate (likely)
- **Certificate Location**: `/etc/kvmd/` (typical PiKVM location)
- **Reverse Proxy**: Proxies requests to KVMD daemon

### KVMD HTTP API
Based on PiKVM architecture, the following endpoints exist:

#### Authentication Required
- All `/api/*` endpoints except `/api/init/*` require authentication
- Authentication methods:
  - X-KVMD-User / X-KVMD-Passwd headers
  - Cookie-based session tokens
  - Optional 2FA (password + TOTP code)

#### GL.iNet Specific Extensions
- `/api/init/init?password=[val]` - Device initialization (pre-auth)
- `/api/init/is_inited` - Check init status (returns country code)
- Firmware upgrade endpoints with ZIP file handling
- AstroWarp cloud service integration
- Fingerbot integration (smart button pusher)

### Redfish API (Optional)
- **Endpoint**: `/redfish/v1`
- **Purpose**: Industry-standard DMTF Redfish for server management
- **Status**: May be available, requires authentication
- **Authentication**: `/redfish/v1` public, other endpoints require auth

## Authentication Mechanisms

### Web Interface / API Authentication
- **Method**: HTTP Basic Authentication (htpasswd-style)
- **Storage**: `/etc/kvmd/htpasswd` (encrypted passwords)
- **Default User**: `admin` (user-set password on first boot)
- **Management Tool**: `kvmd-htpasswd`
  - `kvmd-htpasswd set <user>` - Change password
  - `kvmd-htpasswd add <user>` - Add user
  - `kvmd-htpasswd del <user>` - Remove user
  - `kvmd-htpasswd list` - List users

### Two-Factor Authentication
- **Status**: Optional, configurable
- **Method**: TOTP (Time-based One-Time Password)
- **Usage**: Append 6-digit code to password (e.g., `password123456`)

### SSH Authentication
- **User**: `root`
- **Password**: Same as web admin password
- **Method**: Password authentication
- **Key-based Auth**: Likely supported (standard OpenSSH)

### VNC Authentication
- **Method**: VNCAuth
- **Status**: Typically disabled by default (PiKVM default)
- **Alternative**: Use web interface or SSH tunnel

### First-Boot Initialization
- **Endpoint**: `/api/init/init?password=[val]`
- **Restriction**: Only works once, on unconfigured device
- **Risk**: Unauthenticated endpoint on new devices
- **Mitigation**: Only active before first configuration

## Hardcoded Credentials & Debug Interfaces

### No Default Passwords Found
- **GL.iNet Comet**: Requires user-set password on first boot
- **Factory Reset**: Clears password, requires re-initialization
- **Reset Method**: Hold RESET button for 10 seconds

### Debug Tools Present

#### GDB Debugger
- **Binary**: `/usr/bin/gdb`
- **Status**: Full GNU debugger with symbols
- **Risk**: Can be used to analyze running processes
- **Mitigation**: Requires SSH access (authenticated)

#### Valgrind Profiling
- **Tool**: `/usr/bin/callgrind_control`
- **Purpose**: Performance profiling and memory debugging
- **Risk**: Information disclosure about process internals

#### System Utilities
- **strace**: Not found in binary list
- **lsof**: Not found in binary list
- **tcpdump**: Not found in binary list
- **procrank**: `/usr/bin/procrank` (memory ranking)

### Development Binaries (Should be removed in production)
- `/usr/bin/gdb` - GNU Debugger
- Debug symbols present in binaries ("not stripped")
- Test binaries: `rkmedia_*_test`, `mpi_*_test`
- Factory test tools: `FactoryTest-*`

### Update/Upgrade Interfaces
- **Endpoint**: KVMD API firmware upgrade (POST /api/update or similar)
- **Format**: ZIP file upload
- **Risk**: Potential zip-slip path traversal vulnerability
- **Recommendation**: Verify path sanitization in upgrade handler

## Firewall & Network Security

### Firewall Tools
- **iptables**: Libraries present
  - `libip4tc.so.0.1.0` - IPv4 tables
  - `libip6tc.so.0.1.0` - IPv6 tables
  - `libiptc.so.0.0.0` - Common iptables
- **Status**: Tools available, rules unknown without runtime analysis

### Expected Default Policy
Based on typical KVM-over-IP deployments:
- **INPUT**: ACCEPT or selective allow for service ports
- **OUTPUT**: ACCEPT (allow all outbound)
- **FORWARD**: DROP (device is not a router)

### Network Isolation Recommendations
The device should be deployed on a management/OOB network, isolated from:
- Production networks
- Guest networks
- Internet-facing networks

## Attack Surface Summary

### External Network Attack Surface

| Service | Port | Protocol | Auth Required | Exposure Risk |
|---------|------|----------|---------------|---------------|
| KVMD API | 443/tcp | HTTPS | Yes (except `/api/init/*`) | Medium |
| HTTP Redirect | 80/tcp | HTTP | No | Low |
| Janus WebRTC | 8088/tcp | HTTP | Via KVMD | Medium |
| VNC Server | 5900/tcp | VNC | Yes (if enabled) | Medium-High |
| RTSP Stream | 554/tcp | RTSP | Unknown | Medium |
| SSH | 22/tcp | SSH | Yes | Medium |
| mDNS | 5353/udp | mDNS | No | Low |
| SNMP | 161/udp | SNMP | Community (if enabled) | High (if enabled) |

### Attack Vectors to Consider

#### 1. Unauthenticated Initialization Endpoint
- **Risk**: `/api/init/init` allows password setting on unconfigured devices
- **Impact**: Attacker could initialize device if accessed before legitimate admin
- **Mitigation**: Only works once; use network isolation during deployment

#### 2. Firmware Upload Path Traversal
- **Risk**: ZIP file handling in upgrade API may be vulnerable to zip-slip
- **Impact**: Arbitrary file write, potential RCE
- **Status**: Unknown, requires code review
- **Recommendation**: Audit ZIP extraction in upgrade handler

#### 3. Debug Tools in Production
- **Risk**: GDB, valgrind, test binaries present in production firmware
- **Impact**: Aids attacker in reverse engineering and exploitation
- **Recommendation**: Remove from production builds

#### 4. Default Service Exposure
- **Risk**: All services may be listening on 0.0.0.0 (all interfaces)
- **Impact**: Attack surface on both LAN and WAN (if connected)
- **Mitigation**: Use firewall rules or listen on management interface only

#### 5. SNMP Community Strings
- **Risk**: If SNMP enabled, weak community strings
- **Impact**: Information disclosure, potential configuration changes
- **Status**: Unknown if enabled by default
- **Recommendation**: Disable SNMP or use strong community strings

#### 6. Cloud Service Privacy
- **Risk**: GL.iNet cloud service phones home
- **Impact**: Data privacy concerns, traffic analysis
- **Status**: Optional but integrated in firmware
- **Recommendation**: Use Tailscale or ZeroTier instead for privacy

#### 7. SSL/TLS Certificate Validation
- **Risk**: Self-signed certificates susceptible to MITM
- **Impact**: Credential interception
- **Recommendation**: Use trusted CA certificates or certificate pinning

#### 8. Outdated Build System
- **Risk**: Buildroot 2018.02-rc3 (2018), potentially outdated packages
- **Impact**: Known CVEs in system libraries
- **Recommendation**: Update to current Buildroot and audit package versions

## Recommendations

### For Operators

1. **Network Isolation**: Deploy on dedicated OOB/management VLAN
2. **Firewall Rules**: Restrict access to known management IPs
3. **Disable Unused Services**: Disable VNC, SNMP if not needed
4. **Strong Passwords**: Use strong, unique admin password
5. **Enable 2FA**: Configure TOTP two-factor authentication
6. **Monitor Access**: Review `/api/log` regularly for suspicious activity
7. **Private VPN**: Use Tailscale/ZeroTier instead of cloud service for privacy
8. **Certificate Management**: Replace self-signed cert with CA-signed certificate

### For GL.iNet (Vendor)

1. **Remove Debug Tools**: Strip gdb, valgrind, test binaries from production
2. **Strip Binaries**: Remove debug symbols from production builds
3. **Audit Upgrade Handler**: Review ZIP extraction for path traversal
4. **Update Buildroot**: Migrate to current Buildroot LTS
5. **CVE Scanning**: Implement automated CVE scanning in CI/CD
6. **Minimize Services**: Disable SNMP by default, make VNC opt-in
7. **Firewall by Default**: Ship with restrictive iptables rules
8. **Security Documentation**: Publish security best practices guide

## References

### Analysis Sources
- Firmware: `glkvm-RM1-1.7.2-1128-1764344791.img`
- Build: Buildroot 2018.02-rc3
- Model: GL.iNet Comet (GL-RM1)
- Version: V1.7.2 release1

### External Documentation
- [PiKVM HTTP API Reference](https://docs.pikvm.org/api/)
- [PiKVM Authentication](https://docs.pikvm.org/auth/)
- [GL.iNet Comet Quick Setup](https://docs.gl-inet.com/kvm/en/user_guide/gl-rm1/quick_setup_guide/)
- [Janus WebRTC Gateway](https://janus.conf.meetecho.com/)
- [runZero: Out-of-Band IP KVM Research](https://www.runzero.com/blog/oob-p1-ip-kvm/)

### Related Project Files
- [GPL Binaries Analysis](gpl-binaries.md)
- [Shared Libraries](packages.md)
- [Build Information](build-info.md)
- [Extracted Files](extracted-files.md)
