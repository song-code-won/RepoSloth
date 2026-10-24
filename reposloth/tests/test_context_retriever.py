"""Tests for context retrieval, chunking, and source reference preservation."""

from pathlib import Path
from reposloth.services.context_retriever import ContextRetriever

def test_context_retrieval(tmp_path: Path):
    """Verify retriever indexes source chunks and retrieves relevant snippets with line references."""
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(
        "import jwt\n"
        "def authenticate_user(token):\n"
        "    # Decode JWT\n"
        "    return jwt.decode(token, 'secret', algorithms=['HS256'])\n"
        "def verify_permissions(user):\n"
        "    return user.is_admin\n",
        encoding="utf-8"
    )

    db_file = tmp_path / "database.py"
    db_file.write_text(
        "from sqlalchemy import create_engine\n"
        "def get_connection():\n"
        "    return create_engine('sqlite:///app.db')\n",
        encoding="utf-8"
    )

    retriever = ContextRetriever(tmp_path, ["auth.py", "database.py"])
    results = retriever.retrieve("authenticate_user token")

    assert len(results) > 0
    top = results[0]
    assert top["file"] == "auth.py"
    assert "authenticate_user" in top["text"]
    assert top["start_line"] >= 1
    assert top["end_line"] >= top["start_line"]

def test_empty_query_handling(tmp_path: Path):
    """Verify retriever handles empty or meaningless query gracefully."""
    test_file = tmp_path / "sample.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    retriever = ContextRetriever(tmp_path, ["sample.py"])
    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []
