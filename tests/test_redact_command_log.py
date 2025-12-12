"""Tests for command log redaction script."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from redact_command_log import redact_line


class TestGitHubTokenRedaction:
    """Test GitHub token pattern redaction."""

    def test_github_personal_access_token(self):
        """Test redaction of ghp_ tokens."""
        line = "export TOKEN=ghp_1234567890123456789012345678901234AB"
        assert "ghp_" not in redact_line(line)
        assert "[REDACTED:GITHUB_TOKEN]" in redact_line(line)

    def test_github_oauth_token(self):
        """Test redaction of gho_ tokens."""
        line = (
            "curl -H 'Authorization: token gho_ABCD1234567890123456789012345678EF' api.github.com"
        )
        assert "gho_" not in redact_line(line)
        assert "[REDACTED:GITHUB_OAUTH]" in redact_line(line)

    def test_github_secret_token(self):
        """Test redaction of ghs_ tokens."""
        line = "ghs_9876543210987654321098765432109876XY"
        assert "ghs_" not in redact_line(line)
        assert "[REDACTED:GITHUB_SECRET]" in redact_line(line)

    def test_github_pat_token(self):
        """Test redaction of github_pat_ tokens."""
        line = (
            "github_pat_11ABCDEFG0123456789_"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ABCDEF"
        )
        assert "github_pat_" not in redact_line(line)
        assert "[REDACTED:GITHUB_PAT]" in redact_line(line)


class TestPasswordRedaction:
    """Test password and secret redaction."""

    def test_password_equals(self):
        """Test password=value redaction."""
        line = "mysql -u root -p password=secretpass123"
        redacted = redact_line(line)
        assert "secretpass123" not in redacted
        assert "password=[REDACTED]" in redacted

    def test_passwd_case_insensitive(self):
        """Test case-insensitive PASSWORD redaction."""
        line = "curl -d 'PASSWORD=MyP@ssw0rd' https://example.com"
        redacted = redact_line(line)
        assert "MyP@ssw0rd" not in redacted
        assert "PASSWORD=[REDACTED]" in redacted

    def test_api_key_equals(self):
        """Test api_key=value redaction."""
        line = "API_KEY=sk-1234567890abcdef"
        redacted = redact_line(line)
        assert "sk-1234567890abcdef" not in redacted
        assert "API_KEY=[REDACTED]" in redacted

    def test_apikey_no_separator(self):
        """Test apikey=value redaction (no separator)."""
        line = "apikey=abc123def456"
        redacted = redact_line(line)
        assert "abc123def456" not in redacted
        assert "apikey=[REDACTED]" in redacted

    def test_token_equals(self):
        """Test token=value redaction."""
        line = "Authorization: Bearer token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        redacted = redact_line(line)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "token=[REDACTED]" in redacted


class TestPrivateKeyRedaction:
    """Test private key redaction."""

    def test_rsa_private_key(self):
        """Test RSA private key redaction."""
        line = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890
-----END RSA PRIVATE KEY-----"""
        redacted = redact_line(line)
        assert "MIIEpAIBAAKCAQEA1234567890" not in redacted
        assert "[REDACTED:PRIVATE_KEY]" in redacted

    def test_ec_private_key(self):
        """Test EC private key redaction."""
        line = "-----BEGIN EC PRIVATE KEY-----\nABCD1234\n-----END EC PRIVATE KEY-----"
        redacted = redact_line(line)
        assert "ABCD1234" not in redacted
        assert "[REDACTED:PRIVATE_KEY]" in redacted


class TestEmailRedaction:
    """Test email address redaction."""

    def test_simple_email(self):
        """Test simple email redaction."""
        line = "git config user.email john.doe@example.com"
        redacted = redact_line(line)
        assert "john.doe@example.com" not in redacted
        assert "[REDACTED:EMAIL]" in redacted

    def test_email_with_plus(self):
        """Test email with + sign redaction."""
        line = "user+tag@subdomain.example.org"
        redacted = redact_line(line)
        assert "user+tag@subdomain.example.org" not in redacted
        assert "[REDACTED:EMAIL]" in redacted

    def test_email_in_command(self):
        """Test email within command redaction."""
        line = "curl -d 'email=admin@company.co.uk' https://api.example.com"
        redacted = redact_line(line)
        assert "admin@company.co.uk" not in redacted
        assert "[REDACTED:EMAIL]" in redacted


class TestPersonalPathRedaction:
    """Test personal directory path redaction."""

    def test_macos_user_path(self):
        """Test /Users/username redaction."""
        line = "cd /Users/johndoe/Projects/secret-project"
        redacted = redact_line(line)
        assert "johndoe" not in redacted
        assert "/Users/[REDACTED]/Projects/secret-project" in redacted

    def test_linux_home_path(self):
        """Test /home/username redaction."""
        line = "cp /home/alice/file.txt /tmp/"
        redacted = redact_line(line)
        assert "alice" not in redacted
        assert "/home/[REDACTED]/file.txt" in redacted

    def test_multiple_user_paths(self):
        """Test multiple user paths in one line."""
        line = "rsync /Users/bob/src/ /home/charlie/dst/"
        redacted = redact_line(line)
        assert "bob" not in redacted
        assert "charlie" not in redacted
        assert "/Users/[REDACTED]/src/" in redacted
        assert "/home/[REDACTED]/dst/" in redacted


class TestSSHRedaction:
    """Test SSH URL redaction."""

    def test_ssh_url_with_user(self):
        """Test SSH URL with username redaction."""
        line = "git clone ssh://user123@github.com/repo/project.git"
        redacted = redact_line(line)
        assert "user123" not in redacted
        assert "ssh://[REDACTED]@github.com" in redacted


class TestHTTPAuthRedaction:
    """Test HTTP basic auth redaction."""

    def test_http_basic_auth(self):
        """Test HTTP basic auth in URL."""
        line = "curl https://admin:p@ssw0rd@api.example.com/data"
        redacted = redact_line(line)
        assert "admin" not in redacted
        assert "p@ssw0rd" not in redacted
        assert "https://[REDACTED]:[REDACTED]@api.example.com" in redacted


class TestAWSKeyRedaction:
    """Test AWS credential redaction."""

    def test_aws_access_key(self):
        """Test AWS access key redaction."""
        line = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        redacted = redact_line(line)
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "[REDACTED:AWS_ACCESS_KEY]" in redacted

    def test_aws_secret_key(self):
        """Test AWS secret key redaction."""
        line = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        redacted = redact_line(line)
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted
        assert "[REDACTED:AWS_SECRET_KEY]" in redacted


class TestMultipleRedactions:
    """Test multiple redactions in a single line."""

    def test_password_and_email(self):
        """Test redacting both password and email."""
        line = "curl -u admin@example.com -p password=secret123 https://api.com"
        redacted = redact_line(line)
        assert "admin@example.com" not in redacted
        assert "secret123" not in redacted
        assert "[REDACTED:EMAIL]" in redacted
        assert "password=[REDACTED]" in redacted

    def test_github_token_and_path(self):
        """Test redacting GitHub token and user path."""
        line = "export TOKEN=ghp_ABCD1234567890123456789012345678EF && cd /Users/alice/repo"
        redacted = redact_line(line)
        assert "ghp_" not in redacted
        assert "alice" not in redacted
        assert "[REDACTED:GITHUB_TOKEN]" in redacted
        assert "/Users/[REDACTED]/repo" in redacted


class TestNoRedaction:
    """Test lines that should not be redacted."""

    def test_normal_command(self):
        """Test that normal commands are unchanged."""
        line = "ls -la /tmp"
        assert redact_line(line) == line

    def test_git_status(self):
        """Test git status unchanged."""
        line = "git status"
        assert redact_line(line) == line

    def test_public_paths(self):
        """Test public paths unchanged."""
        line = "cd /usr/local/bin"
        assert redact_line(line) == line


class TestPreservesStructure:
    """Test that redaction preserves command structure."""

    def test_preserves_command_structure(self):
        """Test command structure is preserved."""
        line = "git config user.email test@example.com"
        redacted = redact_line(line)
        assert redacted.startswith("git config user.email")
        assert "[REDACTED:EMAIL]" in redacted

    def test_preserves_line_ending(self):
        """Test line ending is preserved."""
        line = "export TOKEN=ghp_1234567890123456789012345678901234AB\n"
        redacted = redact_line(line)
        assert redacted.endswith("\n")
