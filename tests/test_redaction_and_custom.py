import os
import unittest
from unittest.mock import MagicMock, patch

from git_sensei.providers import AIProvider
from git_sensei.secrets_shield import redact_secrets


class TestRedactionAndCustomAPI(unittest.TestCase):
    def test_redact_secrets_simple(self):
        diff = (
            "diff --git a/src/index.js b/src/index.js\n"
            "--- a/src/index.js\n"
            "+++ b/src/index.js\n"
            "+const token = \"ghp_123456789012345678901234567890123456\";\n"
            "+const pass = \"mysecretpassword\";\n"
        )
        redacted = redact_secrets(diff)
        self.assertNotIn("ghp_123456789012345678901234567890123456", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redact_generic_secret_key(self):
        diff = (
            "diff --git a/config.py b/config.py\n"
            "--- a/config.py\n"
            "+++ b/config.py\n"
            "+secret_key = 'super_secret_value_123456'\n"
        )
        redacted = redact_secrets(diff)
        self.assertNotIn("super_secret_value_123456", redacted)
        self.assertIn("secret_key = '[REDACTED]'", redacted)

    def test_custom_provider_config(self):
        config = {
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "api_key_env": "DEEPSEEK_API_KEY",
            "model": "deepseek-coder"
        }
        provider = AIProvider("deepseek", config)
        self.assertEqual(provider.api_url, "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(provider.api_key_env, "DEEPSEEK_API_KEY")
        self.assertEqual(provider.model, "deepseek-coder")

    @patch("urllib.request.urlopen")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key-123"})
    def test_custom_provider_execution(self, mock_urlopen):
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "feat: test message"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        config = {
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "api_key_env": "DEEPSEEK_API_KEY",
            "model": "deepseek-coder"
        }
        provider = AIProvider("deepseek", config)
        self.assertTrue(provider.check_health())
        
        result = provider.execute("some diff", "system prompt")
        self.assertEqual(result, "feat: test message")
        
        # Verify call parameters
        args = mock_urlopen.call_args[0][0]
        self.assertEqual(args.full_url, "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(args.get_header("Authorization"), "Bearer test-key-123")

    @patch("urllib.request.urlopen")
    def test_local_provider_without_key(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "feat: local message"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        config = {
            "api_url": "http://localhost:11434/v1/chat/completions",
            "model": "llama3"
        }
        provider = AIProvider("ollama", config)
        self.assertTrue(provider.check_health())
        
        result = provider.execute("some diff", "system prompt")
        self.assertEqual(result, "feat: local message")
        
        args = mock_urlopen.call_args[0][0]
        self.assertEqual(args.full_url, "http://localhost:11434/v1/chat/completions")
        self.assertEqual(args.get_header("Authorization"), "Bearer dummy")

if __name__ == "__main__":
    unittest.main()
