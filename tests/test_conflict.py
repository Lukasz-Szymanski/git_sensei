"""Unit tests for conflict resolver."""
from git_sensei.core.conflict_resolver import (
    extract_conflict_sections,
    clean_resolved_content,
    resolve_file_conflict
)
from unittest.mock import MagicMock
import tempfile
import os

def test_extract_conflict_sections():
    sample = """def add(a, b):
<<<<<<< HEAD
    return a + b + 1
=======
    return a + b
>>>>>>> main
"""
    conflicts = extract_conflict_sections(sample)
    assert len(conflicts) == 1
    assert "return a + b + 1" in conflicts[0]["ours"]
    assert "return a + b" in conflicts[0]["theirs"]

def test_clean_resolved_content():
    raw_ai = "```python\ndef add(a, b):\n    return a + b\n```"
    cleaned = clean_resolved_content(raw_ai)
    assert cleaned == "def add(a, b):\n    return a + b"

def test_resolve_file_conflict_mocked():
    sample = """Line 1
<<<<<<< HEAD
Feature branch change
=======
Main branch change
>>>>>>> main
Line 4
"""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tmp:
        tmp.write(sample)
        tmp_path = tmp.name

    try:
        mock_ai = MagicMock()
        mock_ai.execute.return_value = "Line 1\nMerged feature and main change\nLine 4"

        res = resolve_file_conflict(tmp_path, mock_ai)
        assert res["success"] is True
        assert res["conflicts_count"] == 1
        assert "Merged feature and main change" in res["resolved_content"]
        assert not res["has_remaining_markers"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
