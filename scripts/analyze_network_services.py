#!/usr/bin/env python3
"""Analyze network services and attack surface in firmware.

Usage: ./scripts/analyze_network_services.py [firmware.img] [--format FORMAT]

Outputs: TOML (default) or JSON to stdout with source metadata

This script analyzes the firmware for:
- Network-facing services (web servers, SSH, etc.)
- Init scripts and service configurations
- Open ports and protocols
- Authentication mechanisms
- Potential security concerns

Arguments:
    firmware.img      Path to firmware file (optional, downloads default if not provided)
    --format FORMAT   Output format: 'toml' (default) or 'json'
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.analysis_base import AnalysisBase
from lib.firmware import (
    extract_firmware,
    find_squashfs_rootfs,
    get_firmware_path,
)
from lib.logging import error, info, section, success, warn
from lib.output import output_json, output_toml

# Password hash analysis constants
MIN_SHADOW_FIELDS = 2  # Minimum fields in /etc/shadow entry
MIN_HASH_LENGTH = 13  # Minimum length for a valid password hash


@dataclass(frozen=True, slots=True)
class InitScript:
    """An init script found in the firmware."""

    name: str
    size: int


@dataclass(frozen=True, slots=True)
class ServiceBinary:
    """A network service binary found in the firmware."""

    name: str
    path: str
    description: str


@dataclass(frozen=True, slots=True)
class PasswordEntry:
    """A password entry from /etc/shadow or /etc/passwd."""

    username: str
    hash_type: str
    description: str


@dataclass(slots=True)
class NetworkServicesAnalysis(AnalysisBase):
    """Results of network services and attack surface analysis."""

    firmware_file: str
    firmware_size: int
    rootfs_path: str

    # Init scripts
    init_scripts: list[InitScript] = field(default_factory=list)
    systemd_services: list[str] = field(default_factory=list)

    # Web services
    web_servers: list[ServiceBinary] = field(default_factory=list)
    web_frameworks: list[ServiceBinary] = field(default_factory=list)

    # SSH services
    ssh_server: ServiceBinary | None = None

    # Other network services
    network_services: list[ServiceBinary] = field(default_factory=list)

    # Security analysis
    passwd_file_exists: bool = False
    shadow_file_exists: bool = False
    password_entries: list[PasswordEntry] = field(default_factory=list)
    sensitive_files: list[str] = field(default_factory=list)

    # Network configuration
    network_interfaces_exists: bool = False
    firewall_rules: list[str] = field(default_factory=list)

    # Summary counts
    web_server_count: int = 0
    ssh_server_count: int = 0

    # Source metadata for each field
    _source: dict[str, str] = field(default_factory=dict)
    _method: dict[str, str] = field(default_factory=dict)

    def _convert_complex_field(self, key: str, value: Any) -> tuple[bool, Any]:
        """Convert complex fields to serializable format."""
        if key == "init_scripts":
            return True, [{"name": s.name, "size": s.size} for s in value]
        if key in ("web_servers", "web_frameworks", "network_services"):
            return True, [
                {"name": s.name, "path": s.path, "description": s.description} for s in value
            ]
        if key == "ssh_server":
            if value:
                return True, {
                    "name": value.name,
                    "path": value.path,
                    "description": value.description,
                }
            return True, None
        if key == "password_entries":
            return True, [
                {
                    "username": p.username,
                    "hash_type": p.hash_type,
                    "description": p.description,
                }
                for p in value
            ]
        return False, None


def find_init_scripts(rootfs: Path) -> list[InitScript]:
    """Find init scripts in /etc/init.d."""
    init_d = rootfs / "etc" / "init.d"
    if not init_d.exists():
        return []

    scripts = []
    for script in init_d.iterdir():
        if script.is_file():
            scripts.append(InitScript(name=script.name, size=script.stat().st_size))

    return sorted(scripts, key=lambda s: s.name)


def find_systemd_services(rootfs: Path) -> list[str]:
    """Find systemd service files."""
    services = []

    # Check for systemd directories
    systemd_dirs = [rootfs / "etc" / "systemd", rootfs / "lib" / "systemd"]
    if not any(d.exists() for d in systemd_dirs):
        return []

    # Find all .service files
    for service_file in rootfs.rglob("*.service"):
        if service_file.is_file():
            services.append(str(service_file.relative_to(rootfs)))

    return sorted(services)


def find_web_servers(rootfs: Path) -> list[ServiceBinary]:
    """Find web server binaries."""
    web_servers = []
    server_names = {
        "nginx": "Nginx web server",
        "lighttpd": "Lighttpd web server",
        "httpd": "HTTP daemon",
        "apache2": "Apache web server",
        "uvicorn": "Uvicorn ASGI server",
        "gunicorn": "Gunicorn WSGI server",
    }

    for server_name, description in server_names.items():
        for binary in rootfs.rglob(f"{server_name}*"):
            if binary.is_file():
                web_servers.append(
                    ServiceBinary(
                        name=server_name,
                        path=str(binary.relative_to(rootfs)),
                        description=description,
                    )
                )
                break  # Only take first match

    return web_servers


def find_web_frameworks(rootfs: Path) -> list[ServiceBinary]:
    """Find Python web frameworks."""
    frameworks = []

    # Check for aiohttp
    for aiohttp_dir in rootfs.rglob("site-packages/aiohttp*"):
        if aiohttp_dir.is_dir():
            frameworks.append(
                ServiceBinary(
                    name="aiohttp",
                    path="Python package",
                    description="Async HTTP framework",
                )
            )
            break

    # Check for uvicorn
    for uvicorn_dir in rootfs.rglob("site-packages/uvicorn*"):
        if uvicorn_dir.is_dir():
            frameworks.append(
                ServiceBinary(
                    name="uvicorn",
                    path="Python package",
                    description="ASGI server",
                )
            )
            break

    return frameworks


def find_ssh_server(rootfs: Path) -> ServiceBinary | None:
    """Find SSH server (OpenSSH or Dropbear)."""
    # Check for OpenSSH sshd
    for sshd in rootfs.rglob("sshd"):
        if sshd.is_file():
            return ServiceBinary(
                name="sshd",
                path=str(sshd.relative_to(rootfs)),
                description="OpenSSH server",
            )

    # Check for Dropbear
    for dropbear in rootfs.rglob("dropbear"):
        if dropbear.is_file():
            return ServiceBinary(
                name="dropbear",
                path=str(dropbear.relative_to(rootfs)),
                description="Dropbear SSH server",
            )

    return None


def find_network_services(rootfs: Path) -> list[ServiceBinary]:
    """Find other network service binaries."""
    services = []
    service_names = {
        "avahi-daemon": "mDNS/Bonjour",
        "dnsmasq": "DNS/DHCP",
        "hostapd": "WiFi AP",
        "wpa_supplicant": "WiFi client",
        "mosquitto": "MQTT broker",
        "telnetd": "Telnet (insecure)",
        "ftpd": "FTP server",
        "vsftpd": "FTP server",
        "smbd": "Samba/SMB",
        "ntpd": "NTP",
        "chronyd": "NTP",
        "bluetoothd": "Bluetooth",
        "janus": "WebRTC gateway",
    }

    for service_name, description in service_names.items():
        for binary in rootfs.rglob(service_name):
            if binary.is_file():
                services.append(
                    ServiceBinary(
                        name=service_name,
                        path=str(binary.relative_to(rootfs)),
                        description=description,
                    )
                )
                break  # Only take first match

    return services


def _classify_password_hash(password_hash: str) -> tuple[str, str]:
    """Classify a password hash and return (type, description).

    Args:
        password_hash: The password hash from /etc/shadow

    Returns:
        Tuple of (hash_type, description)
    """
    if password_hash in ("", "*", "!"):
        return ("locked", "No password / locked")
    if password_hash == "x":
        return ("shadow", "Password in shadow file")
    if len(password_hash) < MIN_HASH_LENGTH:
        return ("weak", "Weak/short hash (potential issue)")

    # Identify hash type by prefix
    prefix = password_hash[:3]
    hash_types = {
        "$1$": ("md5", "MD5 hash (weak)"),
        "$5$": ("sha256", "SHA-256 hash"),
        "$6$": ("sha512", "SHA-512 hash (strong)"),
        "$y$": ("yescrypt", "yescrypt hash (strong)"),
    }

    return hash_types.get(prefix, (prefix, f"Hash present (type: {prefix})"))


def analyze_shadow_file(rootfs: Path) -> list[PasswordEntry]:
    """Analyze /etc/shadow for password hashes."""
    shadow_file = rootfs / "etc" / "shadow"
    if not shadow_file.exists():
        return []

    entries = []
    try:
        with shadow_file.open() as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) < MIN_SHADOW_FIELDS:
                    continue

                username = parts[0]
                password_hash = parts[1]

                # Classify password hash
                hash_type, description = _classify_password_hash(password_hash)

                entries.append(
                    PasswordEntry(
                        username=username,
                        hash_type=hash_type,
                        description=description,
                    )
                )
    except (OSError, PermissionError):
        warn("Could not read /etc/shadow")

    return entries


def find_sensitive_files(rootfs: Path) -> list[str]:
    """Find files that might contain credentials."""
    etc_dir = rootfs / "etc"
    if not etc_dir.exists():
        return []

    sensitive = []
    try:
        result = subprocess.run(
            ["grep", "-r", "-l", "-i", "-E", "password|secret|api.key|token", str(etc_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines()[:20]:  # Limit to 20 files
            try:
                sensitive.append(str(Path(line).relative_to(rootfs)))
            except ValueError:
                continue
    except (OSError, subprocess.SubprocessError):
        warn("Could not search for sensitive files")

    return sensitive


def find_firewall_rules(rootfs: Path) -> list[str]:
    """Find firewall rule files."""
    rules = []
    try:
        # Look for iptables rules
        for rule_file in rootfs.rglob("*.rules"):
            if "iptables" in str(rule_file):
                rules.append(str(rule_file.relative_to(rootfs)))

        # Look for firewall configs
        for fw_file in rootfs.rglob("firewall*"):
            if fw_file.is_file():
                rules.append(str(fw_file.relative_to(rootfs)))
    except (OSError, PermissionError):
        pass

    return sorted(set(rules))[:5]  # Limit to 5 unique files


def analyze_firmware(firmware_path: str) -> NetworkServicesAnalysis:  # noqa: PLR0912, PLR0915
    """Analyze firmware for network services and attack surface."""
    firmware = Path(firmware_path)

    if not firmware.exists():
        error(f"Firmware file not found: {firmware}")
        sys.exit(1)

    info(f"Analyzing: {firmware}")

    # Get firmware size
    firmware_size = firmware.stat().st_size

    # Extract firmware
    work_dir = Path("/tmp/fw_analysis")
    extract_dir = extract_firmware(firmware, work_dir)
    rootfs = find_squashfs_rootfs(extract_dir)

    info(f"Using rootfs: {rootfs}")

    # Create analysis object
    analysis = NetworkServicesAnalysis(
        firmware_file=firmware.name,
        firmware_size=firmware_size,
        rootfs_path=str(rootfs),
    )

    analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")
    analysis.add_metadata("firmware_size", "filesystem", "Path(firmware).stat().st_size")
    analysis.add_metadata("rootfs_path", "binwalk", "find squashfs-root in extracted firmware")

    # Scan for network services
    section("Scanning for network services")

    # Find init scripts
    analysis.init_scripts = find_init_scripts(rootfs)
    if analysis.init_scripts:
        analysis.add_metadata(
            "init_scripts",
            "filesystem",
            "find /etc/init.d -maxdepth 1 -type f",
        )

    # Find systemd services
    analysis.systemd_services = find_systemd_services(rootfs)
    if analysis.systemd_services:
        analysis.add_metadata(
            "systemd_services",
            "filesystem",
            "find rootfs -name '*.service' -type f",
        )

    # Find web servers
    analysis.web_servers = find_web_servers(rootfs)
    if analysis.web_servers:
        analysis.add_metadata(
            "web_servers",
            "filesystem",
            "find rootfs for nginx, lighttpd, httpd, apache2, uvicorn, gunicorn",
        )

    # Find web frameworks
    analysis.web_frameworks = find_web_frameworks(rootfs)
    if analysis.web_frameworks:
        analysis.add_metadata(
            "web_frameworks",
            "filesystem",
            "find rootfs -path '*/site-packages/aiohttp*' or uvicorn*",
        )

    # Find SSH server
    analysis.ssh_server = find_ssh_server(rootfs)
    if analysis.ssh_server:
        analysis.add_metadata(
            "ssh_server",
            "filesystem",
            "find rootfs for sshd or dropbear",
        )

    # Find other network services
    analysis.network_services = find_network_services(rootfs)
    if analysis.network_services:
        analysis.add_metadata(
            "network_services",
            "filesystem",
            "find rootfs for dnsmasq, hostapd, mosquitto, telnetd, etc.",
        )

    # Security analysis
    section("Security analysis")

    passwd_file = rootfs / "etc" / "passwd"
    analysis.passwd_file_exists = passwd_file.exists()
    if analysis.passwd_file_exists:
        analysis.add_metadata(
            "passwd_file_exists",
            "filesystem",
            "check if /etc/passwd exists",
        )

    shadow_file = rootfs / "etc" / "shadow"
    analysis.shadow_file_exists = shadow_file.exists()
    if analysis.shadow_file_exists:
        analysis.add_metadata(
            "shadow_file_exists",
            "filesystem",
            "check if /etc/shadow exists",
        )
        analysis.password_entries = analyze_shadow_file(rootfs)
        if analysis.password_entries:
            analysis.add_metadata(
                "password_entries",
                "filesystem",
                "parse /etc/shadow and identify hash types",
            )

    # Find sensitive files
    analysis.sensitive_files = find_sensitive_files(rootfs)
    if analysis.sensitive_files:
        analysis.add_metadata(
            "sensitive_files",
            "grep",
            "grep -r -l -i 'password|secret|api.key|token' /etc",
        )

    # Network configuration
    section("Network configuration")

    network_interfaces = rootfs / "etc" / "network" / "interfaces"
    analysis.network_interfaces_exists = network_interfaces.exists()
    if analysis.network_interfaces_exists:
        analysis.add_metadata(
            "network_interfaces_exists",
            "filesystem",
            "check if /etc/network/interfaces exists",
        )

    # Find firewall rules
    analysis.firewall_rules = find_firewall_rules(rootfs)
    if analysis.firewall_rules:
        analysis.add_metadata(
            "firewall_rules",
            "filesystem",
            "find rootfs -name '*.rules' -path '*iptables*' or 'firewall*'",
        )

    # Summary counts
    analysis.web_server_count = len(analysis.web_servers)
    analysis.ssh_server_count = 1 if analysis.ssh_server else 0

    analysis.add_metadata(
        "web_server_count",
        "filesystem",
        "count web server binaries found",
    )
    analysis.add_metadata(
        "ssh_server_count",
        "filesystem",
        "count SSH server binaries found",
    )

    return analysis


# Field order for TOML output
SIMPLE_FIELDS = [
    "firmware_file",
    "firmware_size",
    "rootfs_path",
    "passwd_file_exists",
    "shadow_file_exists",
    "network_interfaces_exists",
    "web_server_count",
    "ssh_server_count",
]

COMPLEX_FIELDS = [
    "init_scripts",
    "systemd_services",
    "web_servers",
    "web_frameworks",
    "ssh_server",
    "network_services",
    "password_entries",
    "sensitive_files",
    "firewall_rules",
]


def main() -> None:
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Analyze network services and attack surface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "firmware",
        nargs="?",
        help="Path to firmware file (downloads default if not provided)",
    )
    parser.add_argument(
        "--format",
        choices=["toml", "json"],
        default="toml",
        help="Output format (default: toml)",
    )
    args = parser.parse_args()

    # Determine paths
    work_dir = Path("/tmp/fw_analysis")

    # Get firmware path
    firmware = get_firmware_path(args.firmware, work_dir)
    firmware_path = str(firmware)

    # Analyze firmware
    analysis = analyze_firmware(firmware_path)

    # Output in requested format
    if args.format == "json":
        print(output_json(analysis))
    else:  # toml
        print(
            output_toml(
                analysis,
                title="Network services and attack surface analysis",
                simple_fields=SIMPLE_FIELDS,
                complex_fields=COMPLEX_FIELDS,
            )
        )

    success("Network services analysis complete")


if __name__ == "__main__":
    main()
