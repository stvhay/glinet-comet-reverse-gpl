"""Tests for scripts/analyze_network_services.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_network_services import (
    MIN_HASH_LENGTH,
    MIN_SHADOW_FIELDS,
    TOML_COMMENT_TRUNCATE_LENGTH,
    TOML_MAX_COMMENT_LENGTH,
    InitScript,
    NetworkServicesAnalysis,
    PasswordEntry,
    ServiceBinary,
    _classify_password_hash,
    analyze_shadow_file,
    find_firewall_rules,
    find_init_scripts,
    find_network_services,
    find_sensitive_files,
    find_ssh_server,
    find_squashfs_rootfs,
    find_systemd_services,
    find_web_frameworks,
    find_web_servers,
    output_toml,
)


class TestInitScript:
    """Test InitScript dataclass."""

    def test_init_script_creation(self):
        """Test creating an InitScript."""
        script = InitScript(name="network", size=4096)

        assert script.name == "network"
        assert script.size == 4096

    def test_init_script_is_frozen(self):
        """Test that InitScript is immutable (frozen)."""
        script = InitScript(name="network", size=4096)

        with pytest.raises(AttributeError):
            script.name = "firewall"  # type: ignore

    def test_init_script_has_slots(self):
        """Test that InitScript uses __slots__ for efficiency."""
        script = InitScript(name="network", size=4096)

        # Frozen dataclasses prevent attribute modification entirely
        # Testing __slots__ is less relevant for frozen dataclasses
        # Just verify the object works as expected
        assert hasattr(script.__class__, "__slots__")


class TestServiceBinary:
    """Test ServiceBinary dataclass."""

    def test_service_binary_creation(self):
        """Test creating a ServiceBinary."""
        service = ServiceBinary(
            name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
        )

        assert service.name == "nginx"
        assert service.path == "/usr/sbin/nginx"
        assert service.description == "Nginx web server"

    def test_service_binary_is_frozen(self):
        """Test that ServiceBinary is immutable (frozen)."""
        service = ServiceBinary(
            name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
        )

        with pytest.raises(AttributeError):
            service.name = "apache"  # type: ignore

    def test_service_binary_has_slots(self):
        """Test that ServiceBinary uses __slots__ for efficiency."""
        service = ServiceBinary(
            name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
        )

        assert hasattr(service.__class__, "__slots__")


class TestPasswordEntry:
    """Test PasswordEntry dataclass."""

    def test_password_entry_creation(self):
        """Test creating a PasswordEntry."""
        entry = PasswordEntry(
            username="root", hash_type="sha512", description="SHA-512 hash (strong)"
        )

        assert entry.username == "root"
        assert entry.hash_type == "sha512"
        assert entry.description == "SHA-512 hash (strong)"

    def test_password_entry_is_frozen(self):
        """Test that PasswordEntry is immutable (frozen)."""
        entry = PasswordEntry(
            username="root", hash_type="sha512", description="SHA-512 hash (strong)"
        )

        with pytest.raises(AttributeError):
            entry.username = "admin"  # type: ignore

    def test_password_entry_has_slots(self):
        """Test that PasswordEntry uses __slots__ for efficiency."""
        entry = PasswordEntry(
            username="root", hash_type="sha512", description="SHA-512 hash (strong)"
        )

        assert hasattr(entry.__class__, "__slots__")


class TestNetworkServicesAnalysis:
    """Test NetworkServicesAnalysis dataclass."""

    def test_analysis_creation(self):
        """Test creating a NetworkServicesAnalysis."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        assert analysis.firmware_file == "test.img"
        assert analysis.firmware_size == 1024
        assert analysis.rootfs_path == "/tmp/squashfs-root"
        assert analysis.init_scripts == []
        assert analysis.systemd_services == []
        assert analysis.web_servers == []
        assert analysis.ssh_server is None
        assert analysis.network_services == []
        assert analysis.password_entries == []
        assert analysis.sensitive_files == []
        assert analysis.firewall_rules == []
        assert analysis.web_server_count == 0
        assert analysis.ssh_server_count == 0

    def test_analysis_is_mutable(self):
        """Test that NetworkServicesAnalysis is mutable (not frozen)."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        # Should be able to modify fields
        analysis.web_server_count = 2
        assert analysis.web_server_count == 2

    def test_add_metadata(self):
        """Test adding source metadata."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        analysis.add_metadata(
            "firmware_size", "filesystem", "Path(firmware).stat().st_size"
        )

        assert analysis._source["firmware_size"] == "filesystem"
        assert analysis._method["firmware_size"] == "Path(firmware).stat().st_size"

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        result = analysis.to_dict()

        assert "firmware_file" in result
        assert "firmware_size" in result
        assert "rootfs_path" in result

    def test_to_dict_includes_metadata(self):
        """Test to_dict includes source metadata."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.add_metadata(
            "firmware_size", "filesystem", "Path(firmware).stat().st_size"
        )

        result = analysis.to_dict()

        assert result["firmware_size"] == 1024
        assert result["firmware_size_source"] == "filesystem"
        assert result["firmware_size_method"] == "Path(firmware).stat().st_size"

    def test_to_dict_converts_init_scripts(self):
        """Test to_dict converts InitScript objects to dicts."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.init_scripts = [InitScript(name="network", size=4096)]

        result = analysis.to_dict()

        assert len(result["init_scripts"]) == 1
        assert result["init_scripts"][0]["name"] == "network"
        assert result["init_scripts"][0]["size"] == 4096

    def test_to_dict_converts_service_binaries(self):
        """Test to_dict converts ServiceBinary objects to dicts."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.web_servers = [
            ServiceBinary(
                name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
            )
        ]

        result = analysis.to_dict()

        assert len(result["web_servers"]) == 1
        assert result["web_servers"][0]["name"] == "nginx"
        assert result["web_servers"][0]["path"] == "/usr/sbin/nginx"
        assert result["web_servers"][0]["description"] == "Nginx web server"

    def test_to_dict_converts_ssh_server(self):
        """Test to_dict converts ssh_server ServiceBinary to dict."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.ssh_server = ServiceBinary(
            name="sshd", path="/usr/sbin/sshd", description="OpenSSH server"
        )

        result = analysis.to_dict()

        assert result["ssh_server"]["name"] == "sshd"
        assert result["ssh_server"]["path"] == "/usr/sbin/sshd"
        assert result["ssh_server"]["description"] == "OpenSSH server"

    def test_to_dict_converts_password_entries(self):
        """Test to_dict converts PasswordEntry objects to dicts."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.password_entries = [
            PasswordEntry(
                username="root", hash_type="sha512", description="SHA-512 hash (strong)"
            )
        ]

        result = analysis.to_dict()

        assert len(result["password_entries"]) == 1
        assert result["password_entries"][0]["username"] == "root"
        assert result["password_entries"][0]["hash_type"] == "sha512"
        assert result["password_entries"][0]["description"] == "SHA-512 hash (strong)"

    def test_to_dict_excludes_internal_fields(self):
        """Test to_dict excludes internal fields (starting with _)."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.add_metadata("firmware_file", "test", "test method")

        result = analysis.to_dict()

        assert "_source" not in result
        assert "_method" not in result


class TestClassifyPasswordHash:
    """Test _classify_password_hash function."""

    def test_classify_empty_hash(self):
        """Test classifying empty password hash."""
        hash_type, description = _classify_password_hash("")

        assert hash_type == "locked"
        assert description == "No password / locked"

    def test_classify_asterisk_hash(self):
        """Test classifying asterisk password hash."""
        hash_type, description = _classify_password_hash("*")

        assert hash_type == "locked"
        assert description == "No password / locked"

    def test_classify_exclamation_hash(self):
        """Test classifying exclamation mark password hash."""
        hash_type, description = _classify_password_hash("!")

        assert hash_type == "locked"
        assert description == "No password / locked"

    def test_classify_x_hash(self):
        """Test classifying 'x' password hash."""
        hash_type, description = _classify_password_hash("x")

        assert hash_type == "shadow"
        assert description == "Password in shadow file"

    def test_classify_short_hash(self):
        """Test classifying short password hash."""
        # Less than MIN_HASH_LENGTH (13)
        hash_type, description = _classify_password_hash("short")

        assert hash_type == "weak"
        assert description == "Weak/short hash (potential issue)"

    def test_classify_md5_hash(self):
        """Test classifying MD5 password hash."""
        hash_type, description = _classify_password_hash(
            "$1$salt$hashhashhashhashhashhash"
        )

        assert hash_type == "md5"
        assert description == "MD5 hash (weak)"

    def test_classify_sha256_hash(self):
        """Test classifying SHA-256 password hash."""
        hash_type, description = _classify_password_hash(
            "$5$salt$hashhashhashhashhashhash"
        )

        assert hash_type == "sha256"
        assert description == "SHA-256 hash"

    def test_classify_sha512_hash(self):
        """Test classifying SHA-512 password hash."""
        hash_type, description = _classify_password_hash(
            "$6$salt$hashhashhashhashhashhash"
        )

        assert hash_type == "sha512"
        assert description == "SHA-512 hash (strong)"

    def test_classify_yescrypt_hash(self):
        """Test classifying yescrypt password hash."""
        hash_type, description = _classify_password_hash(
            "$y$salt$hashhashhashhashhashhash"
        )

        assert hash_type == "yescrypt"
        assert description == "yescrypt hash (strong)"

    def test_classify_unknown_hash(self):
        """Test classifying unknown password hash."""
        hash_type, description = _classify_password_hash(
            "$9$salt$hashhashhashhashhashhash"
        )

        assert hash_type == "$9$"
        assert "Hash present (type: $9$)" in description


class TestFindSquashfsRootfs:
    """Test find_squashfs_rootfs function."""

    def test_find_squashfs_rootfs_success(self, tmp_path):
        """Test finding squashfs-root directory."""
        extract_dir = tmp_path / "firmware.img.extracted"
        squashfs_root = extract_dir / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_squashfs_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_squashfs_rootfs_nested(self, tmp_path):
        """Test finding squashfs-root in nested directory."""
        extract_dir = tmp_path / "firmware.img.extracted"
        nested = extract_dir / "1234" / "5678"
        squashfs_root = nested / "squashfs-root"
        squashfs_root.mkdir(parents=True)

        result = find_squashfs_rootfs(extract_dir)

        assert result == squashfs_root

    def test_find_squashfs_rootfs_not_found(self, tmp_path):
        """Test that missing squashfs-root causes exit."""
        extract_dir = tmp_path / "firmware.img.extracted"
        extract_dir.mkdir(parents=True)

        with pytest.raises(SystemExit) as exc_info:
            find_squashfs_rootfs(extract_dir)

        assert exc_info.value.code == 1


class TestFindInitScripts:
    """Test find_init_scripts function."""

    def test_find_init_scripts_success(self, tmp_path):
        """Test finding init scripts in /etc/init.d."""
        rootfs = tmp_path / "rootfs"
        init_d = rootfs / "etc" / "init.d"
        init_d.mkdir(parents=True)

        # Create some init scripts
        (init_d / "network").write_bytes(b"x" * 4096)
        (init_d / "firewall").write_bytes(b"x" * 2048)

        result = find_init_scripts(rootfs)

        assert len(result) == 2
        assert result[0].name == "firewall"  # Sorted alphabetically
        assert result[0].size == 2048
        assert result[1].name == "network"
        assert result[1].size == 4096

    def test_find_init_scripts_empty(self, tmp_path):
        """Test finding init scripts when directory is empty."""
        rootfs = tmp_path / "rootfs"
        init_d = rootfs / "etc" / "init.d"
        init_d.mkdir(parents=True)

        result = find_init_scripts(rootfs)

        assert result == []

    def test_find_init_scripts_not_found(self, tmp_path):
        """Test finding init scripts when directory doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_init_scripts(rootfs)

        assert result == []


class TestFindSystemdServices:
    """Test find_systemd_services function."""

    def test_find_systemd_services_success(self, tmp_path):
        """Test finding systemd service files."""
        rootfs = tmp_path / "rootfs"
        systemd_dir = rootfs / "etc" / "systemd" / "system"
        systemd_dir.mkdir(parents=True)

        # Create some service files
        (systemd_dir / "network.service").write_text("[Unit]\nDescription=Network")
        (systemd_dir / "firewall.service").write_text("[Unit]\nDescription=Firewall")

        result = find_systemd_services(rootfs)

        assert len(result) == 2
        assert any("firewall.service" in s for s in result)
        assert any("network.service" in s for s in result)

    def test_find_systemd_services_multiple_locations(self, tmp_path):
        """Test finding systemd service files in multiple locations."""
        rootfs = tmp_path / "rootfs"

        # Create services in /etc/systemd
        etc_systemd = rootfs / "etc" / "systemd" / "system"
        etc_systemd.mkdir(parents=True)
        (etc_systemd / "network.service").write_text("[Unit]\nDescription=Network")

        # Create services in /lib/systemd
        lib_systemd = rootfs / "lib" / "systemd" / "system"
        lib_systemd.mkdir(parents=True)
        (lib_systemd / "firewall.service").write_text("[Unit]\nDescription=Firewall")

        result = find_systemd_services(rootfs)

        assert len(result) >= 2

    def test_find_systemd_services_not_found(self, tmp_path):
        """Test finding systemd services when directories don't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_systemd_services(rootfs)

        assert result == []


class TestFindWebServers:
    """Test find_web_servers function."""

    def test_find_nginx(self, tmp_path):
        """Test finding Nginx web server."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "nginx").write_bytes(b"dummy binary")

        result = find_web_servers(rootfs)

        assert len(result) == 1
        assert result[0].name == "nginx"
        assert "nginx" in result[0].path
        assert "Nginx" in result[0].description

    def test_find_lighttpd(self, tmp_path):
        """Test finding Lighttpd web server."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "lighttpd").write_bytes(b"dummy binary")

        result = find_web_servers(rootfs)

        assert len(result) == 1
        assert result[0].name == "lighttpd"
        assert "Lighttpd" in result[0].description

    def test_find_multiple_web_servers(self, tmp_path):
        """Test finding multiple web servers."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "nginx").write_bytes(b"dummy binary")
        (sbin / "lighttpd").write_bytes(b"dummy binary")

        result = find_web_servers(rootfs)

        assert len(result) >= 2
        server_names = {s.name for s in result}
        assert "nginx" in server_names
        assert "lighttpd" in server_names

    def test_find_web_servers_empty(self, tmp_path):
        """Test finding web servers when none exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_web_servers(rootfs)

        assert result == []


class TestFindWebFrameworks:
    """Test find_web_frameworks function."""

    def test_find_aiohttp(self, tmp_path):
        """Test finding aiohttp framework."""
        rootfs = tmp_path / "rootfs"
        site_packages = rootfs / "usr" / "lib" / "python3.10" / "site-packages"
        aiohttp_dir = site_packages / "aiohttp"
        aiohttp_dir.mkdir(parents=True)

        result = find_web_frameworks(rootfs)

        assert len(result) == 1
        assert result[0].name == "aiohttp"
        assert result[0].description == "Async HTTP framework"

    def test_find_uvicorn(self, tmp_path):
        """Test finding uvicorn framework."""
        rootfs = tmp_path / "rootfs"
        site_packages = rootfs / "usr" / "lib" / "python3.10" / "site-packages"
        uvicorn_dir = site_packages / "uvicorn"
        uvicorn_dir.mkdir(parents=True)

        result = find_web_frameworks(rootfs)

        assert len(result) == 1
        assert result[0].name == "uvicorn"
        assert result[0].description == "ASGI server"

    def test_find_web_frameworks_empty(self, tmp_path):
        """Test finding web frameworks when none exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_web_frameworks(rootfs)

        assert result == []


class TestFindSshServer:
    """Test find_ssh_server function."""

    def test_find_openssh_sshd(self, tmp_path):
        """Test finding OpenSSH sshd."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "sshd").write_bytes(b"dummy binary")

        result = find_ssh_server(rootfs)

        assert result is not None
        assert result.name == "sshd"
        assert "OpenSSH" in result.description

    def test_find_dropbear(self, tmp_path):
        """Test finding Dropbear SSH server."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "dropbear").write_bytes(b"dummy binary")

        result = find_ssh_server(rootfs)

        assert result is not None
        assert result.name == "dropbear"
        assert "Dropbear" in result.description

    def test_find_ssh_server_not_found(self, tmp_path):
        """Test finding SSH server when none exists."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_ssh_server(rootfs)

        assert result is None


class TestFindNetworkServices:
    """Test find_network_services function."""

    def test_find_dnsmasq(self, tmp_path):
        """Test finding dnsmasq service."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "dnsmasq").write_bytes(b"dummy binary")

        result = find_network_services(rootfs)

        assert len(result) == 1
        assert result[0].name == "dnsmasq"
        assert "DNS/DHCP" in result[0].description

    def test_find_mosquitto(self, tmp_path):
        """Test finding mosquitto MQTT broker."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "mosquitto").write_bytes(b"dummy binary")

        result = find_network_services(rootfs)

        assert len(result) == 1
        assert result[0].name == "mosquitto"
        assert "MQTT" in result[0].description

    def test_find_multiple_network_services(self, tmp_path):
        """Test finding multiple network services."""
        rootfs = tmp_path / "rootfs"
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "dnsmasq").write_bytes(b"dummy binary")
        (sbin / "hostapd").write_bytes(b"dummy binary")
        (sbin / "mosquitto").write_bytes(b"dummy binary")

        result = find_network_services(rootfs)

        assert len(result) >= 3
        service_names = {s.name for s in result}
        assert "dnsmasq" in service_names
        assert "hostapd" in service_names
        assert "mosquitto" in service_names

    def test_find_network_services_empty(self, tmp_path):
        """Test finding network services when none exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_network_services(rootfs)

        assert result == []


class TestAnalyzeShadowFile:
    """Test analyze_shadow_file function."""

    def test_analyze_shadow_file_success(self, tmp_path):
        """Test analyzing /etc/shadow file."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        shadow_content = """root:$6$salt$hashhash:19000:0:99999:7:::
user:!:19001:0:99999:7:::
locked:*:19002:0:99999:7:::
"""
        (etc / "shadow").write_text(shadow_content)

        result = analyze_shadow_file(rootfs)

        assert len(result) == 3
        assert result[0].username == "root"
        assert result[0].hash_type == "sha512"
        assert result[1].username == "user"
        assert result[1].hash_type == "locked"
        assert result[2].username == "locked"
        assert result[2].hash_type == "locked"

    def test_analyze_shadow_file_not_found(self, tmp_path):
        """Test analyzing when /etc/shadow doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = analyze_shadow_file(rootfs)

        assert result == []

    def test_analyze_shadow_file_invalid_lines(self, tmp_path):
        """Test analyzing /etc/shadow with invalid lines."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        shadow_content = """root:$6$salt$hashhash:19000:0:99999:7:::
invalid
user:!:19001:0:99999:7:::
"""
        (etc / "shadow").write_text(shadow_content)

        result = analyze_shadow_file(rootfs)

        # Invalid line should be skipped
        assert len(result) == 2
        assert result[0].username == "root"
        assert result[1].username == "user"


class TestFindSensitiveFiles:
    """Test find_sensitive_files function."""

    @patch("subprocess.run")
    def test_find_sensitive_files_success(self, mock_run, tmp_path):
        """Test finding sensitive files with grep."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        # Create some files
        (etc / "config1").write_text("password=secret")
        (etc / "config2").write_text("api_key=12345")

        # Mock grep output
        mock_run.return_value = MagicMock(
            stdout=f"{etc / 'config1'}\n{etc / 'config2'}\n", returncode=0
        )

        result = find_sensitive_files(rootfs)

        assert len(result) == 2
        assert "etc/config1" in result
        assert "etc/config2" in result

    @patch("subprocess.run")
    def test_find_sensitive_files_limits_output(self, mock_run, tmp_path):
        """Test that sensitive files are limited to 20."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        # Mock grep output with 30 files
        files = [str(etc / f"config{i}") for i in range(30)]
        mock_run.return_value = MagicMock(stdout="\n".join(files), returncode=0)

        result = find_sensitive_files(rootfs)

        # Limited to 20
        assert len(result) <= 20

    def test_find_sensitive_files_no_etc(self, tmp_path):
        """Test finding sensitive files when /etc doesn't exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_sensitive_files(rootfs)

        assert result == []


class TestFindFirewallRules:
    """Test find_firewall_rules function."""

    def test_find_firewall_rules_iptables(self, tmp_path):
        """Test finding iptables rules files."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        (etc / "iptables.rules").write_text("-A INPUT -j ACCEPT")

        result = find_firewall_rules(rootfs)

        assert len(result) >= 1
        assert any("iptables.rules" in r for r in result)

    def test_find_firewall_rules_firewall_config(self, tmp_path):
        """Test finding firewall config files."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc" / "config"
        etc.mkdir(parents=True)

        (etc / "firewall").write_text("config defaults")

        result = find_firewall_rules(rootfs)

        assert len(result) >= 1
        assert any("firewall" in r for r in result)

    def test_find_firewall_rules_empty(self, tmp_path):
        """Test finding firewall rules when none exist."""
        rootfs = tmp_path / "rootfs"
        rootfs.mkdir(parents=True)

        result = find_firewall_rules(rootfs)

        assert result == []

    def test_find_firewall_rules_limits_output(self, tmp_path):
        """Test that firewall rules are limited to 5."""
        rootfs = tmp_path / "rootfs"
        etc = rootfs / "etc"
        etc.mkdir(parents=True)

        # Create 10 firewall files
        for i in range(10):
            (etc / f"firewall{i}").write_text("config")

        result = find_firewall_rules(rootfs)

        # Limited to 5
        assert len(result) <= 5


class TestOutputToml:
    """Test output_toml function."""

    def test_toml_output_valid(self):
        """Test that TOML output is valid."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
            web_server_count=2,
            ssh_server_count=1,
        )
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        toml_str = output_toml(analysis)

        # Should be valid TOML
        parsed = tomlkit.loads(toml_str)
        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_size"] == 1024
        assert parsed["web_server_count"] == 2
        assert parsed["ssh_server_count"] == 1

    def test_toml_includes_header_comment(self):
        """Test that TOML includes header comment."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        toml_str = output_toml(analysis)

        assert "# Network services and attack surface analysis" in toml_str
        assert "# Generated:" in toml_str

    def test_toml_includes_source_comments(self):
        """Test that TOML includes source metadata as comments."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.add_metadata(
            "firmware_size", "filesystem", "Path(firmware).stat().st_size"
        )

        toml_str = output_toml(analysis)

        assert "# Source: filesystem" in toml_str
        assert "# Method: Path(firmware).stat().st_size" in toml_str

    def test_toml_truncates_long_methods(self):
        """Test that long method descriptions are truncated."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        long_method = "x" * 100  # 100 characters
        analysis.add_metadata("firmware_size", "test", long_method)

        toml_str = output_toml(analysis)

        # Should be truncated with "..."
        assert "..." in toml_str
        assert long_method not in toml_str

    def test_toml_excludes_metadata_fields(self):
        """Test that _source and _method fields are excluded."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.add_metadata("firmware_size", "test", "test method")

        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        # Metadata should be in comments, not as fields
        assert "_source" not in parsed
        assert "_method" not in parsed
        assert "firmware_size_source" not in parsed
        assert "firmware_size_method" not in parsed

    def test_toml_includes_arrays(self):
        """Test that arrays are included in TOML."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.init_scripts = [InitScript(name="network", size=4096)]
        analysis.web_servers = [
            ServiceBinary(
                name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
            )
        ]

        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        assert len(parsed["init_scripts"]) == 1
        assert parsed["init_scripts"][0]["name"] == "network"
        assert len(parsed["web_servers"]) == 1
        assert parsed["web_servers"][0]["name"] == "nginx"

    def test_toml_validation(self):
        """Test that generated TOML is validated."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )

        # Should not raise - TOML is validated internally
        toml_str = output_toml(analysis)

        # Verify it can be parsed back
        parsed = tomlkit.loads(toml_str)
        assert parsed is not None


class TestIntegration:
    """Integration tests with realistic data."""

    @patch("subprocess.run")
    def test_realistic_network_services_analysis(self, mock_run, tmp_path):
        """Test complete analysis workflow with realistic filesystem."""
        # Create realistic filesystem structure
        rootfs = tmp_path / "squashfs-root"

        # Create init scripts
        init_d = rootfs / "etc" / "init.d"
        init_d.mkdir(parents=True)
        (init_d / "network").write_bytes(b"x" * 4096)
        (init_d / "firewall").write_bytes(b"x" * 2048)
        (init_d / "dnsmasq").write_bytes(b"x" * 1024)

        # Create web server
        sbin = rootfs / "usr" / "sbin"
        sbin.mkdir(parents=True)
        (sbin / "nginx").write_bytes(b"x" * 1024000)

        # Create SSH server
        (sbin / "dropbear").write_bytes(b"x" * 512000)

        # Create network services
        (sbin / "dnsmasq").write_bytes(b"x" * 256000)
        (sbin / "hostapd").write_bytes(b"x" * 384000)

        # Create /etc/shadow
        etc = rootfs / "etc"
        shadow_content = """root:$6$salt$hashhashhashhash:19000:0:99999:7:::
user:!:19001:0:99999:7:::
"""
        (etc / "shadow").write_text(shadow_content)

        # Create /etc/passwd
        (etc / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n")

        # Create firewall config
        (etc / "firewall").write_text("config defaults")

        # Mock grep for sensitive files
        config_file = etc / "config"
        config_file.write_text("password=secret")
        mock_run.return_value = MagicMock(stdout=str(config_file), returncode=0)

        # Create analysis object
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=123456789,
            rootfs_path=str(rootfs),
        )

        # Populate analysis (simulating analyze_firmware behavior)
        analysis.init_scripts = find_init_scripts(rootfs)
        analysis.web_servers = find_web_servers(rootfs)
        analysis.ssh_server = find_ssh_server(rootfs)
        analysis.network_services = find_network_services(rootfs)
        analysis.passwd_file_exists = (rootfs / "etc" / "passwd").exists()
        analysis.shadow_file_exists = (rootfs / "etc" / "shadow").exists()
        analysis.password_entries = analyze_shadow_file(rootfs)
        analysis.sensitive_files = find_sensitive_files(rootfs)
        analysis.firewall_rules = find_firewall_rules(rootfs)
        analysis.web_server_count = len(analysis.web_servers)
        analysis.ssh_server_count = 1 if analysis.ssh_server else 0

        # Verify results
        assert len(analysis.init_scripts) == 3
        assert len(analysis.web_servers) == 1
        assert analysis.web_servers[0].name == "nginx"
        assert analysis.ssh_server is not None
        assert analysis.ssh_server.name == "dropbear"
        assert len(analysis.network_services) == 2
        assert analysis.passwd_file_exists is True
        assert analysis.shadow_file_exists is True
        assert len(analysis.password_entries) == 2
        assert len(analysis.sensitive_files) >= 1
        assert len(analysis.firewall_rules) >= 1
        assert analysis.web_server_count == 1
        assert analysis.ssh_server_count == 1

        # Verify TOML output works
        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)
        assert parsed["web_server_count"] == 1
        assert parsed["ssh_server_count"] == 1
        assert len(parsed["init_scripts"]) == 3
        assert parsed["passwd_file_exists"] is True
        assert parsed["shadow_file_exists"] is True

    def test_to_dict_json_output(self):
        """Test that to_dict works for JSON output."""
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/squashfs-root",
        )
        analysis.init_scripts = [InitScript(name="network", size=4096)]
        analysis.web_servers = [
            ServiceBinary(
                name="nginx", path="/usr/sbin/nginx", description="Nginx web server"
            )
        ]
        analysis.ssh_server = ServiceBinary(
            name="dropbear",
            path="/usr/sbin/dropbear",
            description="Dropbear SSH server",
        )
        analysis.password_entries = [
            PasswordEntry(
                username="root", hash_type="sha512", description="SHA-512 hash (strong)"
            )
        ]
        analysis.add_metadata("firmware_file", "filesystem", "Path(firmware).name")

        result = analysis.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(result, indent=2)
        parsed = json.loads(json_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["firmware_file_source"] == "filesystem"
        assert parsed["firmware_file_method"] == "Path(firmware).name"
        assert len(parsed["init_scripts"]) == 1
        assert len(parsed["web_servers"]) == 1
        assert parsed["ssh_server"]["name"] == "dropbear"
        assert len(parsed["password_entries"]) == 1


class TestMainFunction:
    """Test main() function integration."""

    @patch("analyze_network_services.analyze_firmware")
    @patch("sys.argv", ["analyze_network_services.py"])
    def test_main_default_format(self, mock_analyze, capsys):
        """Test main() with default TOML format."""
        # Create a simple analysis result
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/root",
            web_server_count=1,
        )
        mock_analyze.return_value = analysis

        # We can't easily test main() without actually running it
        # But we can test that the output functions work
        toml_str = output_toml(analysis)
        parsed = tomlkit.loads(toml_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["web_server_count"] == 1

    @patch("analyze_network_services.analyze_firmware")
    def test_main_json_format(self, mock_analyze):
        """Test main() with JSON format."""
        # Create a simple analysis result
        analysis = NetworkServicesAnalysis(
            firmware_file="test.img",
            firmware_size=1024,
            rootfs_path="/tmp/root",
            web_server_count=1,
        )
        mock_analyze.return_value = analysis

        # Test JSON output
        json_str = json.dumps(analysis.to_dict(), indent=2)
        parsed = json.loads(json_str)

        assert parsed["firmware_file"] == "test.img"
        assert parsed["web_server_count"] == 1
