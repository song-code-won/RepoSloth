"""Secret filter service for redacting credentials, tokens, API keys, and sensitive filenames."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Tuple, List

# Patterns targeting high-entropy credentials, tokens, passwords, and private keys
SECRET_PATTERNS = [
    # AWS Access Key ID
    (re.compile(r'\b(AKIA[0-9A-Z]{16})\b'), "[REDACTED_AWS_KEY]"),
    # AWS Secret Key
    (re.compile(r'(?i)(aws_secret_access_key|aws_secret_key)\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?'), r'\1=[REDACTED_SECRET]'),
    # Generic API Keys / Tokens
    (re.compile(r'(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key|client[_-]?secret)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{12,120})["\']'), r'\1="[REDACTED_TOKEN]"'),
    # Passwords in assignment
    (re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\'\r\n]{6,100})["\']'), r'\1="[REDACTED_PASSWORD]"'),
    # Private Key blocks
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----'), "[REDACTED_PRIVATE_KEY_BLOCK]"),
    # GitHub Personal Access Token (classic & fine-grained)
    (re.compile(r'\b(ghp_[A-Za-z0-9_]{36}|github_pat_[A-Za-z0-9_]{82})\b'), "[REDACTED_GITHUB_TOKEN]"),
    # Generic Bearer tokens
    (re.compile(r'(?i)bearer\s+([A-Za-z0-9\-._~+/]+=*)'), 'Bearer [REDACTED_BEARER_TOKEN]'),
    # Database connection strings with passwords: postgresql://user:pass@host:5432/db
    (re.compile(r'([a-zA-Z0-9+]+://[^:]+:)([^@]+)(@[^/\s]+)'), r'\1[REDACTED_PASSWORD]\3'),
]

# Sensitive file names that should never be processed into AI prompts
SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials.json", "service_account.json", "service-account.json",
    "client_secrets.json", "private_key.pem", "privatekey.pem",
    ".pgpass", ".netrc", ".dockercfg", "key.keystore"
}


class SecretFilter:
    """Filters and sanitizes sensitive files and text snippets before AI processing."""

    @staticmethod
    def is_sensitive_filename(path: Path) -> bool:
        """Checks if a file name or any of its suffixes matches dangerous credential files."""
        name_lower = path.name.lower()
        if name_lower in SENSITIVE_FILENAMES:
            return True
        if name_lower.startswith(".env") and not name_lower.endswith(".example"):
            return True
        if name_lower.endswith(".pem") or name_lower.endswith(".key") or name_lower.endswith(".pfx") or name_lower.endswith(".p12"):
            return True
        return False

    @staticmethod
    def sanitize_text(content: str) -> Tuple[str, int]:
        """
        Redacts sensitive tokens, keys, passwords, and private key blocks from text.
        Returns (sanitized_text, count_of_redactions).
        """
        redactions_count = 0
        sanitized = content

        for pattern, replacement in SECRET_PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                redactions_count += len(matches)
                sanitized = pattern.sub(replacement, sanitized)

        return sanitized, redactions_count
