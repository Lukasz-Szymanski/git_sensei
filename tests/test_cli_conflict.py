"""CLI tests for sensei conflict."""
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from git_sensei.main import app

runner = CliRunner()

def test_conflict_cmd_no_conflicts():
    with patch("git_sensei.main.get_conflicted_files", return_value=[]):
        result = runner.invoke(app, ["conflict"])
        assert result.exit_code == 0
        assert "No git merge conflicts found" in result.output

def test_conflict_cmd_auto_apply():
    mock_ai = MagicMock()
    mock_res = {
        "success": True,
        "filepath": "foo.py",
        "conflicts_count": 1,
        "original_content": "old",
        "resolved_content": "resolved text",
        "has_remaining_markers": False
    }

    with patch("git_sensei.main.get_conflicted_files", return_value=["foo.py"]), \
         patch("git_sensei.main.AIProvider", return_value=mock_ai), \
         patch("git_sensei.main.resolve_file_conflict", return_value=mock_res), \
         patch("builtins.open", MagicMock()), \
         patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["conflict", "--apply"])
        assert result.exit_code == 0
        assert "Resolved 1 conflict block(s)" in result.output
        assert "Saved resolution and staged: foo.py" in result.output
        mock_run.assert_called_with(["git", "add", "foo.py"], check=False)
