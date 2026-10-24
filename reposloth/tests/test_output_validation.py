"""Tests for Ollama client connection handling, error states, and mocked AI responses."""

from unittest.mock import MagicMock, patch
from reposloth.services.ollama_client import OllamaClient
from reposloth.services.code_explainer import CodeExplainer
from reposloth.services.report_generator import ReportGenerator

def test_ollama_missing_daemon():
    """Verify clean error reporting when Ollama daemon is not running."""
    client = OllamaClient(host="http://localhost:9999")  # Unused port
    status = client.check_connection()

    assert status["connected"] is False
    assert status["error"] is not None
    assert "cannot connect" in status["error"].lower()

def test_code_explainer_with_mocked_ollama(tmp_path):
    """Verify CodeExplainer handles mocked AI inference without requiring a downloaded model."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = {
        "response": "## Project Overview\nRepoSloth is a local codebase explainer tool.",
        "success": True,
        "error": None
    }

    explainer = CodeExplainer(mock_client)
    scan_data = {
        "repo_path": str(tmp_path),
        "repo_name": "TestRepo",
        "total_files": 3,
        "total_lines": 120,
        "language_stats": {"Python": {"files": 3, "lines": 120}},
        "manifests": {"requirements.txt": ["streamlit"]},
        "entrypoint_candidates": ["app.py"],
        "file_list": ["app.py", "utils.py", "config.py"]
    }

    result = explainer.explain_repository(scan_data, model="qwen2.5-coder:7b")
    assert result["success"] is True
    assert "RepoSloth" in result["response"]
    mock_client.generate.assert_called_once()

def test_report_generation(tmp_path):
    """Verify ReportGenerator compiles statistics, insights, and AI summary into clean markdown."""
    scan_data = {
        "repo_path": str(tmp_path),
        "repo_name": "DemoApp",
        "total_files": 5,
        "total_lines": 350,
        "language_stats": {"Python": {"files": 5, "lines": 350}},
        "entrypoint_candidates": ["main.py"],
        "skipped_secret_files": [".env"],
        "skipped_binary_count": 2,
        "insights": {
            "large_files": [{"path": "core.py", "lines": 450}],
            "deeply_nested": ["src/a/b/c/d/deep.py"]
        }
    }
    ai_summary = "This is a clean Python service."

    report_md = ReportGenerator.generate_overview_report(scan_data, ai_summary)

    assert "# RepoSloth Analysis Report: DemoApp" in report_md
    assert "core.py" in report_md
    assert ".env" in report_md
    assert "This is a clean Python service." in report_md
