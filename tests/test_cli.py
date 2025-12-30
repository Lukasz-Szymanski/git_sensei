import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typer.testing import CliRunner
from main import app

runner = CliRunner()


class TestUseCommand(unittest.TestCase):
    """Tests for 'sensei use' command."""

    def setUp(self):
        """Create a temporary directory for test config files."""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, ".sensei.toml")

    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.test_dir)

    @patch("main.config_mgr")
    def test_use_valid_provider(self, mock_config):
        """'sensei use claude' should set claude as default."""
        mock_config.list_providers.return_value = {
            "gemini": "Google Gemini",
            "claude": "Claude Code"
        }
        mock_config.set_default_provider.return_value = True

        result = runner.invoke(app, ["use", "claude"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Default set to 'claude'", result.stdout)
        mock_config.set_default_provider.assert_called_once_with("claude")

    @patch("main.config_mgr")
    def test_use_invalid_provider(self, mock_config):
        """'sensei use nonexistent' should fail with error."""
        mock_config.list_providers.return_value = {
            "gemini": "Google Gemini",
            "claude": "Claude Code"
        }

        result = runner.invoke(app, ["use", "nonexistent"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Provider 'nonexistent' not found", result.stdout)

    @patch("main.config_mgr")
    def test_use_shows_error(self, mock_config):
        """'sensei use invalid' should show error."""
        mock_config.list_providers.return_value = {
            "gemini": "Google Gemini",
            "claude": "Claude Code"
        }

        result = runner.invoke(app, ["use", "invalid"])

        self.assertIn("not found", result.stdout)


class TestListProvidersCommand(unittest.TestCase):
    """Tests for 'sensei ls' command."""

    @patch("main.config_mgr")
    def test_list_providers(self, mock_config):
        """'sensei ls' should list all providers."""
        mock_config.list_providers.return_value = {
            "gemini": "Google Gemini",
            "claude": "Claude Code"
        }
        mock_config.get_default_provider.return_value = "gemini"

        result = runner.invoke(app, ["ls"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("gemini", result.stdout)
        self.assertIn("claude", result.stdout)

    @patch("main.config_mgr")
    def test_list_providers_marks_default(self, mock_config):
        """'sensei ls' should mark default provider with *."""
        mock_config.list_providers.return_value = {
            "gemini": "Google Gemini",
            "claude": "Claude Code"
        }
        mock_config.get_default_provider.return_value = "claude"

        result = runner.invoke(app, ["ls"])

        # Default provider should be marked
        lines = result.stdout.split('\n')
        claude_line = [l for l in lines if "claude" in l][0]
        self.assertTrue(claude_line.startswith("*"))


class TestCheckCommand(unittest.TestCase):
    """Tests for 'sensei check' command."""

    @patch("main.AIProvider")
    @patch("main.config_mgr")
    def test_check_provider_found(self, mock_config, mock_provider_class):
        """'sensei check' should show success when provider is found."""
        mock_config.get_default_provider.return_value = "gemini"
        mock_config.get_provider_config.return_value = {
            "command": "gemini \"{system}\""
        }

        mock_provider = MagicMock()
        mock_provider.check_health.return_value = True
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(app, ["check"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("OK", result.stdout)

    @patch("main.AIProvider")
    @patch("main.config_mgr")
    def test_check_provider_not_found(self, mock_config, mock_provider_class):
        """'sensei check' should show error when provider executable not found."""
        mock_config.get_default_provider.return_value = "gemini"
        mock_config.get_provider_config.return_value = {
            "command": "gemini \"{system}\""
        }

        mock_provider = MagicMock()
        mock_provider.check_health.return_value = False
        mock_provider_class.return_value = mock_provider

        result = runner.invoke(app, ["check"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("NOT FOUND", result.stdout)

    @patch("main.config_mgr")
    def test_check_unknown_provider(self, mock_config):
        """'sensei check unknown' should fail."""
        mock_config.get_provider_config.return_value = None

        result = runner.invoke(app, ["check", "unknown"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Provider 'unknown' not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
