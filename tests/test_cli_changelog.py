"""CLI tests for sensei changelog."""
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from git_sensei.main import app

runner = CliRunner()

def test_changelog_cmd_no_commits():
    with patch("git_sensei.main.get_commits_since", return_value=[]):
        result = runner.invoke(app, ["changelog"])
        assert result.exit_code == 0
        assert "No commits found" in result.output

def test_changelog_cmd_local_fallback():
    sample_commits = [
        {"hash": "1234567", "subject": "feat: awesome feature"},
        {"hash": "890abcd", "subject": "fix: bug in parser"},
    ]
    mock_ai = MagicMock()
    mock_ai.execute.return_value = None

    with patch("git_sensei.main.get_commits_since", return_value=sample_commits), \
         patch("git_sensei.main.AIProvider", return_value=mock_ai):
        result = runner.invoke(app, ["changelog", "-v", "v1.0.0"], input="n\n")
        assert result.exit_code == 0
        assert "Found 2 commit(s)" in result.output
        assert "v1.0.0" in result.output
        assert "awesome feature" in result.output
        assert "bug in parser" in result.output
