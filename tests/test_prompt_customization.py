import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ConfigManager, DEFAULT_CONFIG
from git_utils import get_recent_commits
from main import build_prompt_with_context


class TestPromptCustomization(unittest.TestCase):
    """Test suite for Milestone 1: Custom Prompts & Few-Shot History."""

    def test_default_prompt_config_loading(self):
        """Verify that default prompt config values are correctly loaded."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cfg = cm.get_prompt_config()
            self.assertEqual(cfg["language"], "en")
            self.assertEqual(cfg["style"], "conventional")
            self.assertEqual(cfg["max_length"], 72)
            self.assertEqual(cfg["template"], "conventional")
            self.assertEqual(cfg["custom"]["header"], "")
            self.assertEqual(cfg["custom"]["footer"], "")
            self.assertEqual(cfg["few_shot"], 3)

    def test_custom_prompt_config_loading(self):
        """Verify that user overrides merge correctly with the default configuration."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "prompt": {
                    "language": "es",
                    "style": "emoji",
                    "template": "my-template",
                    "custom": {
                        "header": "My Header"
                    }
                }
            }
            cfg = cm.get_prompt_config()
            self.assertEqual(cfg["language"], "es")
            self.assertEqual(cfg["style"], "emoji")
            self.assertEqual(cfg["template"], "my-template")
            self.assertEqual(cfg["custom"]["header"], "My Header")
            self.assertEqual(cfg["max_length"], 72)
            self.assertEqual(cfg["custom"]["footer"], "")
            self.assertEqual(cfg["few_shot"], 3)

    def test_template_file_path_resolution(self):
        """Verify that if template refers to a file path, we read and return the file's contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_template_path = os.path.join(tmpdir, "template.txt")
            with open(temp_template_path, "w", encoding="utf-8") as f:
                f.write("This is a custom file template content.")

            with patch.object(ConfigManager, 'load_config'):
                cm = ConfigManager()
                cm.config = {
                    "prompt": {
                        "template": temp_template_path
                    }
                }
                cfg = cm.get_prompt_config()
                self.assertEqual(cfg["template"], "This is a custom file template content.")

    def test_get_recent_commits_success(self):
        """Verify get_recent_commits fetches and parses commits correctly with delimiter."""
        mock_output = "feat: add feature A\n===COMMIT_MSG_DELIMITER===\nfix: fix bug B\n===COMMIT_MSG_DELIMITER===\n"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            
            commits = get_recent_commits(limit=3, start_ref="HEAD")
            self.assertEqual(commits, ["feat: add feature A", "fix: fix bug B"])
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("git", args)
            self.assertIn("log", args)
            self.assertIn("-3", args)
            self.assertIn("HEAD", args)

    def test_get_recent_commits_head_prev(self):
        """Verify get_recent_commits handles HEAD~1 correctly."""
        mock_output = "chore: release 1.0.0\n===COMMIT_MSG_DELIMITER===\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            commits = get_recent_commits(limit=1, start_ref="HEAD~1")
            self.assertEqual(commits, ["chore: release 1.0.0"])
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("HEAD~1", args)

    def test_get_recent_commits_failure_fallback(self):
        """Verify get_recent_commits returns [] gracefully on failure."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            commits = get_recent_commits(limit=3, start_ref="HEAD")
            self.assertEqual(commits, [])

    def test_build_prompt_with_context_default_fallback(self):
        """Verify that when config is default, it falls back to the original placeholder replacement."""
        base_prompt = "Header\n{context}\n{issue_footer}"
        git_context = {
            "context_summary": "Type: feat; Closes issue #123",
            "branch_type": "feat",
            "issue_id": "#123"
        }
        
        prompt_cfg = {
            "language": "en",
            "style": "conventional",
            "max_length": 72,
            "template": "conventional",
            "custom": {
                "header": "",
                "footer": ""
            },
            "few_shot": 3
        }
        
        prompt = build_prompt_with_context(
            base_prompt=base_prompt,
            git_context=git_context,
            prompt_cfg=prompt_cfg,
            recent_commits=["feat: previous commit"]
        )
        self.assertIn("CONTEXT: Type: feat; Closes issue #123", prompt)
        self.assertIn("SUGGESTED TYPE: feat", prompt)
        self.assertIn("Closes #123", prompt)
        self.assertNotIn("ADDITIONAL RULES:", prompt)
        self.assertNotIn("RECENT COMMITS:", prompt)

    def test_build_prompt_with_context_custom_template(self):
        """Verify that custom template compiles correctly with header, summary, few-shot and footer."""
        prompt_cfg = {
            "template": "custom",
            "custom": {
                "header": "Custom Header Instructions",
                "footer": "Custom Footer Instructions"
            },
            "few_shot": 2
        }
        git_context = {
            "context_summary": "Context summary data"
        }
        recent_commits = ["commit 1", "commit 2", "commit 3"]
        
        prompt = build_prompt_with_context(
            base_prompt="Original base prompt (should be ignored)",
            git_context=git_context,
            prompt_cfg=prompt_cfg,
            recent_commits=recent_commits
        )
        
        self.assertIn("Custom Header Instructions", prompt)
        self.assertIn("Context: Context summary data", prompt)
        self.assertIn("Few-shot examples:\n- commit 1\n- commit 2", prompt)
        self.assertNotIn("commit 3", prompt)
        self.assertIn("Custom Footer Instructions", prompt)
        self.assertNotIn("Original base prompt", prompt)

    def test_build_prompt_with_context_additional_rules(self):
        """Verify that non-default styles/languages are appended as additional rules and reference commits."""
        base_prompt = "Base Prompt\n{context}\n{issue_footer}"
        prompt_cfg = {
            "language": "fr",
            "style": "emoji",
            "max_length": 50,
            "template": "conventional",
            "few_shot": 1
        }
        git_context = {
            "context_summary": "Context summary",
            "issue_id": "#456"
        }
        recent_commits = ["chore: clean files"]
        
        prompt = build_prompt_with_context(
            base_prompt=base_prompt,
            git_context=git_context,
            prompt_cfg=prompt_cfg,
            recent_commits=recent_commits
        )
        
        self.assertIn("Base Prompt", prompt)
        self.assertIn("ADDITIONAL RULES:", prompt)
        self.assertIn("- Language: fr", prompt)
        self.assertIn("- Style: emoji", prompt)
        self.assertIn("- Max length: 50 characters", prompt)
        self.assertIn("RECENT COMMITS:", prompt)
        self.assertIn("chore: clean files", prompt)

    def test_build_prompt_with_context_scope(self):
        """Verify that scope is included in the context of build_prompt_with_context."""
        base_prompt = "Header\n{context}"
        git_context = {
            "context_summary": "Type: feat; Scope: auth",
            "branch_type": "feat",
            "scope": "auth"
        }
        prompt_cfg = {
            "language": "en",
            "style": "conventional",
            "max_length": 72,
            "template": "conventional",
            "few_shot": 3
        }
        prompt = build_prompt_with_context(
            base_prompt=base_prompt,
            git_context=git_context,
            prompt_cfg=prompt_cfg,
            recent_commits=[]
        )
        self.assertIn("SUGGESTED SCOPE: auth", prompt)


if __name__ == "__main__":
    unittest.main()
