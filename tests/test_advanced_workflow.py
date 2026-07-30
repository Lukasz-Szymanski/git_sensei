import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_sensei.git_utils import fetch_issue_context
from git_sensei.main import app
from typer.testing import CliRunner

runner = CliRunner()

class TestFetchIssueContext(unittest.TestCase):
    @patch('git_sensei.git_utils.shutil.which')
    @patch('git_sensei.git_utils.subprocess.check_output')
    def test_fetch_issue_context_success(self, mock_check_output, mock_which):
        mock_which.return_value = "/usr/bin/gh"
        mock_check_output.return_value = "Issue Title\n\nIssue Body"
        
        result = fetch_issue_context("#42")
        
        self.assertEqual(result, "--- START EXTERNAL ISSUE CONTENT ---\nIssue Title\n\nIssue Body\n--- END EXTERNAL ISSUE CONTENT ---")
        mock_check_output.assert_called_with(["gh", "issue", "view", "42"], stderr=subprocess.DEVNULL, text=True)

    @patch('git_sensei.git_utils.shutil.which')
    def test_fetch_issue_context_no_gh(self, mock_which):
        mock_which.return_value = None
        result = fetch_issue_context("#42")
        self.assertIsNone(result)

    def test_fetch_issue_context_empty(self):
        self.assertIsNone(fetch_issue_context(""))
        self.assertIsNone(fetch_issue_context(None))
        self.assertIsNone(fetch_issue_context("feat/login"))


class TestAdvancedCLICommands(unittest.TestCase):
    
    @patch('git_sensei.main.shutil.which')
    @patch('git_sensei.main.subprocess.check_output')
    @patch('git_sensei.main.typer.confirm')
    @patch('git_sensei.providers.AIProvider')
    @patch('git_sensei.main.subprocess.run')
    def test_squash_command_success(self, mock_run, mock_ai_provider, mock_confirm, mock_check_output, mock_which):
        mock_which.return_value = "/usr/bin/git"
        
        def mock_check_output_side_effect(args, **kwargs):
            if "log" in args and "--count" not in args:
                return "1a2b3c feat: one\n4d5e6f fix: two"
            elif "rev-list" in args and "--count" in args:
                return "2"
            return ""
            
        mock_check_output.side_effect = mock_check_output_side_effect
        mock_confirm.return_value = True
        
        mock_ai_instance = MagicMock()
        mock_ai_instance.execute.return_value = "pick 1a2b3c\nfixup 4d5e6f"
        mock_ai_provider.return_value = mock_ai_instance
        
        result = runner.invoke(app, ["squash", "-p", "claude"])
        
        self.assertIn("Analyzing commits with AI to generate a rebase plan", result.stdout)
        self.assertIn("Executing git rebase -i", result.stdout)
        mock_run.assert_called()

    @patch('git_sensei.main.shutil.which')
    @patch('git_sensei.main.subprocess.check_output')
    @patch('git_sensei.main.typer.confirm')
    @patch('git_sensei.providers.AIProvider')
    @patch('git_sensei.main.subprocess.run')
    def test_pr_command_success(self, mock_run, mock_ai_provider, mock_confirm, mock_check_output, mock_which):
        def mock_which_side_effect(cmd):
            return f"/usr/bin/{cmd}"
        mock_which.side_effect = mock_which_side_effect
        
        def mock_check_output_side_effect(args, **kwargs):
            if "log" in args:
                return "- feat: one\n- fix: two"
            elif "diff" in args:
                return "diff --git a/file b/file..."
            return ""
            
        mock_check_output.side_effect = mock_check_output_side_effect
        mock_confirm.return_value = True
        
        mock_ai_instance = MagicMock()
        mock_ai_instance.execute.return_value = "## Title: Add feature\n## Motivation\nAdded new stuff."
        mock_ai_provider.return_value = mock_ai_instance
        
        result = runner.invoke(app, ["pr", "-p", "claude"])
        
        self.assertIn("Generated Pull Request", result.stdout)
        self.assertIn("Title: Add feature", result.stdout)
        self.assertIn("Body:\n## Motivation", result.stdout)
        self.assertIn("Pull Request created successfully!", result.stdout)
        mock_run.assert_called()


if __name__ == "__main__":
    unittest.main()
