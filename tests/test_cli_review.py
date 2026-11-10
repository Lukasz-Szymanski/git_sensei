"""CLI tests for sensei review."""
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from git_sensei.main import app

runner = CliRunner()

def test_review_cmd_no_staged():
    with patch("git_sensei.main.get_staged_diff_filtered", return_value=("", {})):
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "No staged changes to review." in result.output

def test_review_cmd_with_clean_staged():
    fake_diff = "diff --git a/foo.py b/foo.py\n+print('hello')"
    fake_ai_response = "LGTM!\nSUMMARY: All changes look good."
    mock_ai = MagicMock()
    mock_ai.execute.return_value = fake_ai_response

    with patch("git_sensei.main.get_staged_diff_filtered", return_value=(fake_diff, {})), \
         patch("git_sensei.main.AIProvider", return_value=mock_ai):
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "LGTM" in result.output

def test_review_cmd_strict_mode_blocks():
    fake_diff = "diff --git a/sec.py b/sec.py\n+token = 'xyz'"
    fake_ai_response = "[CRITICAL] (sec.py:1): Leaked token -> Redact token\nSUMMARY: Found 1 critical issue"
    mock_ai = MagicMock()
    mock_ai.execute.return_value = fake_ai_response

    with patch("git_sensei.main.get_staged_diff_filtered", return_value=(fake_diff, {})), \
         patch("git_sensei.main.AIProvider", return_value=mock_ai):
        result = runner.invoke(app, ["review", "--strict"])
        assert result.exit_code == 1
        assert "Strict mode: Critical review issues detected!" in result.output

