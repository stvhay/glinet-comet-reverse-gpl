#!/usr/bin/env bash
# Analyze network services and attack surface
#
# Usage: ./scripts/analyze-network-services.sh [firmware.img]
#
# Outputs: output/network-services.md
#
# This script analyzes the firmware for:
# - Network-facing services (web servers, SSH, etc.)
# - Init scripts and service configurations
# - Open ports and protocols
# - Authentication mechanisms
# - Potential security concerns

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

# Initialize
init_dirs
require_command binwalk

# Get firmware and extract
FIRMWARE=$(get_firmware "${1:-}")
info "Analyzing network services in: $FIRMWARE"

EXTRACT_DIR=$(extract_firmware "$FIRMWARE")
ROOTFS=$(find_rootfs "$EXTRACT_DIR")

info "Using rootfs: $ROOTFS"

section "Scanning for network services"

# Generate output
{
    generate_header "Network Services & Attack Surface Analysis" \
        "Analysis of network-facing services and potential security concerns."

    echo "## Service Discovery"
    echo ""

    # Find init scripts
    echo "### Init Scripts"
    echo ""
    echo "Services started at boot:"
    echo ""
    echo '```'
    if [[ -d "$ROOTFS/etc/init.d" ]]; then
        # List init scripts with size
        find "$ROOTFS/etc/init.d" -maxdepth 1 -type f -printf "%f %s\n" 2>/dev/null | \
            sort | head -30 || echo "No init.d scripts found"
    fi
    echo '```'
    echo ""

    # Find systemd services if present
    if [[ -d "$ROOTFS/etc/systemd" || -d "$ROOTFS/lib/systemd" ]]; then
        echo "### Systemd Services"
        echo ""
        echo '```'
        find "$ROOTFS" -name "*.service" -type f 2>/dev/null | head -30 || echo "No systemd services found"
        echo '```'
        echo ""
    fi

    # Check for web servers
    echo "## Web Services"
    echo ""

    echo "### Web Server Binaries"
    echo ""
    echo "| Binary | Path | Notes |"
    echo "|--------|------|-------|"

    for webserver in nginx lighttpd httpd apache2 uvicorn gunicorn; do
        found=$(find "$ROOTFS" -name "$webserver*" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            echo "| $webserver | ${found#"$ROOTFS"} | Found |"
        fi
    done

    # Check for Python web frameworks
    if find "$ROOTFS" -path "*/site-packages/aiohttp*" -type d 2>/dev/null | grep -q .; then
        echo "| aiohttp | Python package | Async HTTP |"
    fi
    if find "$ROOTFS" -path "*/site-packages/uvicorn*" -type d 2>/dev/null | grep -q .; then
        echo "| uvicorn | Python package | ASGI server |"
    fi

    echo ""

    # Web server configs
    echo "### Web Server Configuration"
    echo ""
    for conf in nginx.conf lighttpd.conf httpd.conf; do
        found=$(find "$ROOTFS" -name "$conf" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            echo "#### $conf"
            echo ""
            echo '```'
            head -50 "$found" 2>/dev/null || echo "Could not read config"
            echo '```'
            echo ""
        fi
    done

    # Check for SSH
    echo "## SSH Service"
    echo ""

    sshd=$(find "$ROOTFS" -name "sshd" -type f 2>/dev/null | head -1 || true)
    dropbear=$(find "$ROOTFS" -name "dropbear" -type f 2>/dev/null | head -1 || true)

    if [[ -n "$sshd" ]]; then
        echo "- **OpenSSH sshd found:** ${sshd#"$ROOTFS"}"
        sshd_config=$(find "$ROOTFS" -name "sshd_config" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$sshd_config" ]]; then
            echo ""
            echo "### sshd_config"
            echo ""
            echo '```'
            grep -v "^#" "$sshd_config" 2>/dev/null | grep -v "^$" | head -30 || echo "Could not read config"
            echo '```'
        fi
    elif [[ -n "$dropbear" ]]; then
        echo "- **Dropbear SSH found:** ${dropbear#"$ROOTFS"}"
    else
        echo "- No SSH server found"
    fi
    echo ""

    # Check for other network services
    echo "## Other Network Services"
    echo ""
    echo "| Service | Binary | Description |"
    echo "|---------|--------|-------------|"

    # Common network services to look for
    declare -A services
    services["avahi-daemon"]="mDNS/Bonjour"
    services["dnsmasq"]="DNS/DHCP"
    services["hostapd"]="WiFi AP"
    services["wpa_supplicant"]="WiFi client"
    services["mosquitto"]="MQTT broker"
    services["telnetd"]="Telnet (insecure)"
    services["ftpd"]="FTP server"
    services["vsftpd"]="FTP server"
    services["smbd"]="Samba/SMB"
    services["ntpd"]="NTP"
    services["chronyd"]="NTP"
    services["bluetoothd"]="Bluetooth"
    services["janus"]="WebRTC gateway"

    for svc in "${!services[@]}"; do
        found=$(find "$ROOTFS" -name "$svc" -type f 2>/dev/null | head -1 || true)
        if [[ -n "$found" ]]; then
            echo "| $svc | ${found#"$ROOTFS"} | ${services[$svc]} |"
        fi
    done

    echo ""

    # Check for hardcoded credentials
    echo "## Security Analysis"
    echo ""

    echo "### Password Files"
    echo ""
    if [[ -f "$ROOTFS/etc/passwd" ]]; then
        echo "#### /etc/passwd"
        echo ""
        echo '```'
        cat "$ROOTFS/etc/passwd" 2>/dev/null || echo "Could not read"
        echo '```'
        echo ""
    fi

    if [[ -f "$ROOTFS/etc/shadow" ]]; then
        echo "#### /etc/shadow"
        echo ""
        echo '```'
        cat "$ROOTFS/etc/shadow" 2>/dev/null || echo "Could not read (permission denied is expected)"
        echo '```'
        echo ""

        # Check for empty passwords or known hashes
        echo "### Password Analysis"
        echo ""
        while IFS=: read -r user hash rest; do
            if [[ "$hash" == "" || "$hash" == "*" || "$hash" == "!" ]]; then
                echo "- **$user**: No password / locked"
            elif [[ "$hash" == "x" ]]; then
                echo "- **$user**: Password in shadow file"
            elif [[ ${#hash} -lt 13 ]]; then
                echo "- **$user**: Weak/short hash (potential issue)"
            else
                hash_type="${hash:0:3}"
                # shellcheck disable=SC2016 # These are literal password hash prefixes, not variables
                case "$hash_type" in
                    '$1$') echo "- **$user**: MD5 hash (weak)" ;;
                    '$5$') echo "- **$user**: SHA-256 hash" ;;
                    '$6$') echo "- **$user**: SHA-512 hash (strong)" ;;
                    '$y$') echo "- **$user**: yescrypt hash (strong)" ;;
                    *) echo "- **$user**: Hash present (type: ${hash_type})" ;;
                esac
            fi
        done < "$ROOTFS/etc/shadow" 2>/dev/null || true
        echo ""
    fi

    # Look for API keys or tokens in configs
    echo "### Potential Sensitive Data"
    echo ""
    echo "Files containing potential credentials:"
    echo ""
    echo '```'
    grep -r -l -i "password\|secret\|api.key\|token" "$ROOTFS/etc" 2>/dev/null | \
        sed "s|^$ROOTFS||" | head -20 || echo "None found in /etc"
    echo '```'
    echo ""

    # Network configuration
    echo "## Network Configuration"
    echo ""

    if [[ -f "$ROOTFS/etc/network/interfaces" ]]; then
        echo "### /etc/network/interfaces"
        echo ""
        echo '```'
        cat "$ROOTFS/etc/network/interfaces" 2>/dev/null || echo "Could not read"
        echo '```'
        echo ""
    fi

    # Firewall rules
    echo "### Firewall Configuration"
    echo ""
    iptables_rules=$(find "$ROOTFS" -name "*.rules" -path "*iptables*" -o -name "firewall*" 2>/dev/null | head -5)
    if [[ -n "$iptables_rules" ]]; then
        echo "Firewall rule files found:"
        echo ""
        echo '```'
        echo "$iptables_rules"
        echo '```'
    else
        echo "No explicit firewall rules found."
    fi
    echo ""

    # Summary
    echo "## Summary"
    echo ""
    echo "| Category | Finding |"
    echo "|----------|---------|"

    # Count services
    web_count=$(find "$ROOTFS" -name "nginx" -o -name "lighttpd" -o -name "httpd" 2>/dev/null | wc -l | tr -d ' ')
    ssh_count=$(find "$ROOTFS" -name "sshd" -o -name "dropbear" 2>/dev/null | wc -l | tr -d ' ')

    echo "| Web servers | $web_count found |"
    echo "| SSH servers | $ssh_count found |"

    if [[ -f "$ROOTFS/etc/shadow" ]]; then
        echo "| Password storage | Shadow file present |"
    fi

} > "$OUTPUT_DIR/network-services.md"

success "Wrote network-services.md"
