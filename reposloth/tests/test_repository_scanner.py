"""Tests for repository scanner and safe traversal."""

import pytest
from pathlib import Path
from reposloth.services.repository_scanner import RepositoryScanner
from reposloth.services.language_detector import LanguageDetector

def test_empty_repository(tmp_path: Path):
    """Test scanner on an empty directory."""
    scanner = RepositoryScanner(tmp_path)
    result = scanner.scan()

    assert result["total_files"] == 0
    assert result["total_lines"] == 0
    assert result["file_list"] == []
    assert result["entrypoint_candidates"] == []

def test_ignored_directories_and_binaries(tmp_path: Path):
    """Test that node_modules, .git, venv, and binary files are correctly skipped."""
    # Create valid files
    (tmp_path / "main.py").write_text("print('hello world')\n", encoding="utf-8")
    (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

    # Create ignored folders
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.js").write_text("console.log('ignored');", encoding="utf-8")

    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "compiled.pyc").write_bytes(b"\x00\x01\x02")

    # Create binary file
    (tmp_path / "graphic.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    scanner = RepositoryScanner(tmp_path)
    result = scanner.scan()

    assert result["total_files"] == 2
    assert "main.py" in result["file_list"]
    assert "utils.py" in result["file_list"]
    assert not any("node_modules" in f for f in result["file_list"])
    assert not any("__pycache__" in f for f in result["file_list"])
    assert result["skipped_binary_count"] == 1
    assert "main.py" in result["entrypoint_candidates"]

def test_language_detection(tmp_path: Path):
    """Test language detection across Python, JS, Markdown, Dockerfile."""
    assert LanguageDetector.detect_language(Path("app.py")) == "Python"
    assert LanguageDetector.detect_language(Path("index.js")) == "JavaScript"
    assert LanguageDetector.detect_language(Path("Dockerfile")) == "Dockerfile"
    assert LanguageDetector.detect_language(Path("README.md")) == "Markdown"
