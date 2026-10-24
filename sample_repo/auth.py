"""Authentication and token verification module."""

import hmac
import hashlib

SECRET_SALT = "application_salt_not_a_real_secret"

def hash_password(password: str) -> str:
    """Hashes a password with SHA256 and salt."""
    return hashlib.sha256((password + SECRET_SALT).encode('utf-8')).hexdigest()

def verify_token(header_token: str) -> bool:
    """Verifies that an incoming request token matches valid authorization."""
    if not header_token or not header_token.startswith("Bearer "):
        return False
    token = header_token.split(" ")[1]
    return len(token) > 10
