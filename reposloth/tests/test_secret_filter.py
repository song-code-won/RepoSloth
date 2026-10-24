"""Tests for secret filtering and credential redaction."""

from pathlib import Path
from reposloth.services.secret_filter import SecretFilter

def test_sensitive_filenames_detected():
    """Verify sensitive files are detected and flagged."""
    assert SecretFilter.is_sensitive_filename(Path(".env")) is True
    assert SecretFilter.is_sensitive_filename(Path(".env.production")) is True
    assert SecretFilter.is_sensitive_filename(Path("id_rsa")) is True
    assert SecretFilter.is_sensitive_filename(Path("credentials.json")) is True
    assert SecretFilter.is_sensitive_filename(Path("server.key")) is True
    assert SecretFilter.is_sensitive_filename(Path(".env.example")) is False
    assert SecretFilter.is_sensitive_filename(Path("config.py")) is False

def test_token_and_key_redaction():
    """Verify high-entropy keys, passwords, and tokens are redacted."""
    sample_code = """
    # Configuration
    AWS_ACCESS_KEY = "AKIA1234567890ABCDEF"
    API_KEY = "sk-live-1234567890abcdef1234567890"
    DB_PASSWORD = "SuperSecretPassword123!"
    GITHUB_PAT = "ghp_111122223333444455556666777788889999"
    """

    sanitized, count = SecretFilter.sanitize_text(sample_code)

    assert count >= 3
    assert "AKIA1234567890ABCDEF" not in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "SuperSecretPassword123!" not in sanitized
    assert "ghp_111122223333444455556666777788889999" not in sanitized

def test_private_key_redaction():
    """Verify PEM private keys are thoroughly redacted."""
    pem = """
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0Y1o8cW0bY1V8W8G7x
    -----END RSA PRIVATE KEY-----
    """
    sanitized, count = SecretFilter.sanitize_text(pem)
    assert count >= 1
    assert "[REDACTED_PRIVATE_KEY_BLOCK]" in sanitized
