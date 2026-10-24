"""Archive validation service with zip-slip / directory traversal prevention."""

from __future__ import annotations
import os
import zipfile
from pathlib import Path
from typing import Tuple, List

# Limits for safe extraction
MAX_EXTRACT_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB max uncompressed
MAX_FILE_COUNT = 5000                       # Max 5,000 files
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024    # 10 MB single file max


class ArchiveValidationError(Exception):
    """Raised when an archive fails safety or format verification."""
    pass


class ArchiveValidator:
    """Validates and safely extracts repository ZIP archives."""

    @staticmethod
    def validate_and_extract(
        zip_path_or_file, 
        dest_dir: Path,
        max_size: int = MAX_EXTRACT_SIZE_BYTES,
        max_files: int = MAX_FILE_COUNT
    ) -> Tuple[bool, str, List[Path]]:
        """
        Safely validates and extracts a zip archive, preventing zip-slip vulnerabilities,
        decompression bombs, and arbitrary file write outside the destination directory.

        Returns (success: bool, message: str, extracted_files: list[Path])
        """
        dest_path = Path(dest_dir).resolve()
        dest_path.mkdir(parents=True, exist_ok=True)
        extracted_files: List[Path] = []

        try:
            with zipfile.ZipFile(zip_path_or_file, 'r') as zf:
                total_uncompressed_size = 0
                file_count = 0

                # Inspection pass before extracting any file
                for info in zf.infolist():
                    file_count += 1
                    if file_count > max_files:
                        raise ArchiveValidationError(
                            f"Archive exceeds maximum file count limit ({max_files} files)."
                        )

                    total_uncompressed_size += info.file_size
                    if total_uncompressed_size > max_size:
                        raise ArchiveValidationError(
                            f"Archive uncompressed size exceeds safety limit ({max_size / (1024*1024):.1f} MB)."
                        )

                    if info.file_size > MAX_SINGLE_FILE_BYTES:
                        raise ArchiveValidationError(
                            f"Archive contains a file exceeding single-file limit ({info.filename}: {info.file_size / (1024*1024):.1f} MB)."
                        )

                    # Zip-Slip / Path Traversal Check
                    # Normalizing path and ensuring it resides strictly inside dest_path
                    target_candidate = (dest_path / info.filename).resolve()
                    try:
                        target_candidate.relative_to(dest_path)
                    except ValueError:
                        raise ArchiveValidationError(
                            f"Illegal path traversal attempt detected in archive entry: {info.filename}"
                        )

                # Safe extraction pass
                for info in zf.infolist():
                    target_candidate = (dest_path / info.filename).resolve()
                    
                    # Double-check traversal safety
                    if not str(target_candidate).startswith(str(dest_path)):
                        raise ArchiveValidationError(
                            f"Path traversal detected during extraction: {info.filename}"
                        )

                    if info.is_dir():
                        target_candidate.mkdir(parents=True, exist_ok=True)
                    else:
                        target_candidate.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info) as src, open(target_candidate, 'wb') as dst:
                            # Stream copy with byte limit check
                            written = 0
                            while chunk := src.read(65536):
                                written += len(chunk)
                                if written > MAX_SINGLE_FILE_BYTES:
                                    raise ArchiveValidationError(
                                        f"File '{info.filename}' exceeded decompressed size limit while writing."
                                    )
                                dst.write(chunk)
                        extracted_files.append(target_candidate)

            return True, f"Successfully extracted {len(extracted_files)} files.", extracted_files

        except zipfile.BadZipFile:
            return False, "Uploaded file is not a valid or readable ZIP archive.", []
        except ArchiveValidationError as ave:
            return False, f"Security/Validation Error: {str(ave)}", []
        except Exception as e:
            return False, f"Unexpected error during archive extraction: {str(e)}", []
