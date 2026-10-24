"""Tests for ZIP archive validation and Zip-Slip traversal prevention."""

import io
import zipfile
import pytest
from pathlib import Path
from reposloth.services.archive_validator import ArchiveValidator, ArchiveValidationError

def test_safe_zip_extraction(tmp_path: Path):
    """Test extracting a standard benign ZIP file."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("src/main.py", "print('hello safe zip')")
        zf.writestr("README.md", "# Test Safe Archive")

    zip_buffer.seek(0)
    dest = tmp_path / "extracted"
    success, msg, files = ArchiveValidator.validate_and_extract(zip_buffer, dest)

    assert success is True
    assert len(files) == 2
    assert (dest / "src" / "main.py").exists()
    assert (dest / "README.md").exists()

def test_zip_slip_traversal_prevention(tmp_path: Path):
    """Test that path traversal attempts (e.g. ../../etc/passwd) are rejected."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Dangerous zip-slip entry
        zf.writestr("../../malicious.txt", "exploit payload")

    zip_buffer.seek(0)
    dest = tmp_path / "extracted_slip"
    success, msg, files = ArchiveValidator.validate_and_extract(zip_buffer, dest)

    assert success is False
    assert "traversal" in msg.lower()
    assert not (tmp_path / "malicious.txt").exists()

def test_oversized_file_limit(tmp_path: Path):
    """Test rejection when archive exceeds single-file or total size limit."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("big.txt", "A" * 1000)

    zip_buffer.seek(0)
    dest = tmp_path / "extracted_limit"
    # Set artificial max_size to 500 bytes
    success, msg, files = ArchiveValidator.validate_and_extract(zip_buffer, dest, max_size=500)

    assert success is False
    assert "limit" in msg.lower()
