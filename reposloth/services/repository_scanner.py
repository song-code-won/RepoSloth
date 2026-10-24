"""Repository scanner service for discovering files, respecting ignore rules, and building statistics."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from reposloth.services.language_detector import LanguageDetector
from reposloth.services.secret_filter import SecretFilter

# Default directories excluded from scanning
DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".tox", ".mypy_cache", ".ruff_cache",
    "dist", "build", "target", "out", "bin", "obj", ".idea", ".vscode",
    ".next", ".nuxt", ".output", "vendor", "bundle", "coverage", ".turbo"
}

# Binary and oversized extensions excluded from text/code analysis
BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".iso",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".pyc",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".db", ".sqlite", ".sqlite3"
}

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB limit for source files analyzed in detail
MAX_REPO_FILES = 2000             # Max files to index per repo


class RepositoryScanner:
    """Scans and analyzes directory trees safely, ignoring binaries, secrets, and generated artifacts."""

    def __init__(self, repo_path: str | Path, extra_ignore_dirs: Optional[Set[str]] = None):
        self.repo_path = Path(repo_path).resolve()
        self.ignored_dirs = set(DEFAULT_IGNORED_DIRS)
        if extra_ignore_dirs:
            self.ignored_dirs.update(extra_ignore_dirs)

        self._custom_ignore_patterns: List[str] = self._load_gitignore()

    def _load_gitignore(self) -> List[str]:
        """Loads repository .gitignore if present."""
        gitignore_path = self.repo_path / ".gitignore"
        patterns: List[str] = []
        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                for line in gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("#"):
                        patterns.append(cleaned)
            except Exception:
                pass
        return patterns

    def is_ignored(self, path: Path) -> bool:
        """Determines if a path or any ancestor directory should be ignored."""
        try:
            rel = path.relative_to(self.repo_path)
        except ValueError:
            return True

        parts = rel.parts
        for part in parts:
            if part in self.ignored_dirs:
                return True
            if part.startswith(".") and part != ".":
                # Hidden directories like .terraform, .cache, etc.
                if len(parts) > 1 and part != parts[-1]:
                    return True

        # Custom simple gitignore pattern matching
        rel_str = str(rel).replace("\\", "/")
        for pat in self._custom_ignore_patterns:
            pat_clean = pat.rstrip("/")
            if pat_clean in parts or rel_str == pat_clean or rel_str.startswith(pat_clean + "/"):
                return True

        return False

    def scan(self) -> Dict[str, Any]:
        """
        Executes a safe read-only crawl of the repository.
        Returns a rich dictionary containing:
        - file_tree
        - language_breakdown
        - total_files, total_lines, total_size_bytes
        - entrypoint_candidates
        - manifest_summary
        - complexity_insights
        """
        if not self.repo_path.exists():
            return {"error": f"Repository path does not exist: {self.repo_path}"}
        if not self.repo_path.is_dir():
            return {"error": f"Repository path is not a directory: {self.repo_path}"}

        all_valid_files: List[Path] = []
        skipped_secret_files: List[str] = []
        skipped_binary_files: List[str] = []
        skipped_oversized_files: List[str] = []
        
        language_stats: Dict[str, Dict[str, int]] = {}
        total_lines = 0
        total_size = 0

        # Walk directory
        for root, dirs, files in os.walk(self.repo_path, topdown=True):
            # Prune ignored directories in-place for performance
            dirs[:] = [d for d in dirs if not self.is_ignored(Path(root) / d)]

            for file in files:
                file_path = Path(root) / file
                
                if self.is_ignored(file_path):
                    continue

                # Check secret files
                if SecretFilter.is_sensitive_filename(file_path):
                    try:
                        rel = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
                        skipped_secret_files.append(rel)
                    except ValueError:
                        pass
                    continue

                # Check binary files
                if file_path.suffix.lower() in BINARY_EXTENSIONS:
                    try:
                        rel = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
                        skipped_binary_files.append(rel)
                    except ValueError:
                        pass
                    continue

                # Check file size limit
                try:
                    fsize = file_path.stat().st_size
                except (OSError, PermissionError):
                    continue

                if fsize > MAX_FILE_SIZE_BYTES:
                    try:
                        rel = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
                        skipped_oversized_files.append(f"{rel} ({fsize // 1024} KB)")
                    except ValueError:
                        pass
                    continue

                all_valid_files.append(file_path)
                total_size += fsize

                if len(all_valid_files) >= MAX_REPO_FILES:
                    break
            
            if len(all_valid_files) >= MAX_REPO_FILES:
                break

        # Calculate language and line count statistics
        large_files: List[Dict[str, Any]] = []
        deeply_nested: List[str] = []

        for p in all_valid_files:
            lang = LanguageDetector.detect_language(p)
            line_count = 0
            try:
                # Count lines without loading entire file into memory
                with open(p, "rb") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = 0

            total_lines += line_count

            if lang not in language_stats:
                language_stats[lang] = {"files": 0, "lines": 0}
            language_stats[lang]["files"] += 1
            language_stats[lang]["lines"] += line_count

            try:
                rel = str(p.relative_to(self.repo_path)).replace("\\", "/")
                # Check for large files heuristic (> 400 lines)
                if line_count > 400:
                    large_files.append({"path": rel, "lines": line_count})
                # Check for deeply nested heuristic (> 4 directory levels)
                if rel.count("/") >= 4:
                    deeply_nested.append(rel)
            except ValueError:
                pass

        # Sort large files descending
        large_files.sort(key=lambda x: x["lines"], reverse=True)

        # Detect entrypoints and manifests
        entrypoints = LanguageDetector.identify_entrypoints(self.repo_path, all_valid_files)
        manifests = LanguageDetector.detect_manifests(self.repo_path)

        # Relative file paths for UI
        relative_file_list = []
        for p in all_valid_files:
            try:
                relative_file_list.append(str(p.relative_to(self.repo_path)).replace("\\", "/"))
            except ValueError:
                pass
        relative_file_list.sort()

        return {
            "repo_path": str(self.repo_path),
            "repo_name": self.repo_path.name,
            "total_files": len(all_valid_files),
            "total_lines": total_lines,
            "total_size_bytes": total_size,
            "file_list": relative_file_list,
            "language_stats": language_stats,
            "entrypoint_candidates": entrypoints,
            "manifests": manifests,
            "skipped_secret_files": skipped_secret_files,
            "skipped_binary_count": len(skipped_binary_files),
            "skipped_oversized_files": skipped_oversized_files,
            "insights": {
                "large_files": large_files[:10],
                "deeply_nested": deeply_nested[:10]
            }
        }
