# Security Policy

## Scope

This project contains analysis scripts and documentation only. It does not
include deployed services, proprietary firmware, or user-facing applications.

Security concerns relevant to this project include:

- **Script injection** - Malicious input to analysis scripts (e.g., crafted filenames)
- **Supply chain** - Compromised dependencies in the Nix flake or Python packages
- **Sensitive data leaks** - Accidental commit of proprietary firmware, credentials, or secrets

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch (latest) | Yes |
| Older commits | No |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Instead, use [GitHub's private vulnerability reporting](https://github.com/stvhay/glinet-comet-reverse-gpl/security/advisories/new) to submit a report.

Include:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: Within 7 days
- **Assessment**: Within 14 days
- **Fix (if applicable)**: Best effort, typically within 30 days

## Security Practices

This project follows these practices to reduce risk:

- **No binaries in repo** - `.gitignore` excludes firmware files and extracted contents
- **Reproducible environment** - Nix flake pins all system dependencies
- **CI validation** - All commits to `main` pass automated tests and linting
- **Pre-push hooks** - Pytest runs before code reaches the remote
