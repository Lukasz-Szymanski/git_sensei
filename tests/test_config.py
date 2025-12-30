import unittest
from unittest.mock import patch, mock_open
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Tests for ConfigManager class."""

    def test_default_provider(self):
        """Default provider should be 'gemini' if no config exists."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {"core": {"default_provider": "gemini"}, "providers": {}}
            self.assertEqual(cm.get_default_provider(), "gemini")

    def test_list_providers(self):
        """list_providers should return dict of name -> description."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {},
                "providers": {
                    "gemini": {"description": "Google Gemini", "command": "gemini"},
                    "claude": {"description": "Claude Code", "command": "claude"},
                }
            }
            providers = cm.list_providers()
            self.assertEqual(providers["gemini"], "Google Gemini")
            self.assertEqual(providers["claude"], "Claude Code")

    def test_get_provider_config(self):
        """get_provider_config should return provider dict or None."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {},
                "providers": {
                    "gemini": {"description": "Google Gemini", "command": "gemini \"{system}\""},
                }
            }
            cfg = cm.get_provider_config("gemini")
            self.assertEqual(cfg["command"], "gemini \"{system}\"")

            cfg_none = cm.get_provider_config("nonexistent")
            self.assertIsNone(cfg_none)


class TestSetDefaultProvider(unittest.TestCase):
    """Tests for ConfigManager.set_default_provider method."""

    def setUp(self):
        """Create a temporary directory for test config files."""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, ".sensei.toml")

    def tearDown(self):
        """Remove temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_set_default_provider_creates_new_file(self):
        """set_default_provider should create config file if it doesn't exist."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {"default_provider": "gemini"},
                "providers": {"claude": {"description": "Claude"}}
            }

            with patch.object(cm, 'get_config_path', return_value=self.config_path):
                result = cm.set_default_provider("claude")

            self.assertTrue(result)
            self.assertTrue(os.path.exists(self.config_path))

            with open(self.config_path, "r") as f:
                content = f.read()
            self.assertIn('default_provider = "claude"', content)

    def test_set_default_provider_updates_existing_file(self):
        """set_default_provider should update existing config file."""
        # Create existing config
        with open(self.config_path, "w") as f:
            f.write('[core]\ndefault_provider = "gemini"\n')

        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {"default_provider": "gemini"},
                "providers": {"claude": {"description": "Claude"}}
            }

            with patch.object(cm, 'get_config_path', return_value=self.config_path):
                result = cm.set_default_provider("claude")

            self.assertTrue(result)

            with open(self.config_path, "r") as f:
                content = f.read()
            self.assertIn('default_provider = "claude"', content)
            self.assertNotIn('default_provider = "gemini"', content)

    def test_set_default_provider_invalid_provider(self):
        """set_default_provider should return False for unknown provider."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {"default_provider": "gemini"},
                "providers": {"gemini": {"description": "Gemini"}}
            }

            result = cm.set_default_provider("nonexistent")
            self.assertFalse(result)

    def test_set_default_provider_updates_memory(self):
        """set_default_provider should update in-memory config."""
        with patch.object(ConfigManager, 'load_config'):
            cm = ConfigManager()
            cm.config = {
                "core": {"default_provider": "gemini"},
                "providers": {"claude": {"description": "Claude"}}
            }

            with patch.object(cm, 'get_config_path', return_value=self.config_path):
                cm.set_default_provider("claude")

            self.assertEqual(cm.get_default_provider(), "claude")


if __name__ == "__main__":
    unittest.main()
