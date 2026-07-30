import unittest
import os
import json
import tempfile
from typer.testing import CliRunner
from git_sensei.main import app
from git_sensei.core.stats import get_stats_file_path, record_commit_stat

from unittest.mock import patch

class TestCLIDiagnostics(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.stats_path = os.path.join(self.temp_dir.name, "stats.json")
        self.patcher = patch("git_sensei.core.stats.get_stats_file_path", return_value=self.stats_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_stats_recording_and_display(self):
        # Initial stats call (should show no stats message)
        result = self.runner.invoke(app, ["stats"])
        self.assertIn("No statistics recorded yet", result.stdout)

        # Record a stat
        record_commit_stat("gemini-api", "accepted", "feat", 50)
        record_commit_stat("gemini-api", "rejected", "fix", 30)

        # Retrieve visual stats
        result = self.runner.invoke(app, ["stats"])
        self.assertIn("Commits generated:  2", result.stdout)
        self.assertIn("Acceptance rate:    50%", result.stdout)
        self.assertIn("Average msg length: 40 chars", result.stdout)

        # Retrieve JSON stats
        result = self.runner.invoke(app, ["stats", "--json"])
        data = json.loads(result.stdout)
        self.assertEqual(data["generated_attempts"], 2)
        self.assertEqual(data["decisions"]["accepted"], 1)

        # Reset stats
        result = self.runner.invoke(app, ["stats", "--reset"])
        self.assertIn("Statistics cleared", result.stdout)
        self.assertFalse(os.path.exists(self.stats_path))

    def test_lint_command_valid(self):
        result = self.runner.invoke(app, ["lint", "feat(cli): add diagnostic commands"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commit message is valid", result.stdout)

    def test_lint_command_invalid(self):
        result = self.runner.invoke(app, ["lint", "invalid format message"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("validation failed", result.output)

    def test_lint_command_long_line(self):
        long_msg = "feat: " + ("a" * 80)
        result = self.runner.invoke(app, ["lint", long_msg])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("exceeds 72 characters", result.output)

    def test_lint_command_disallowed_markdown(self):
        result = self.runner.invoke(app, ["lint", "feat: update `README`"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("disallowed markdown", result.output)

    def test_lint_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: repair broken behavior")
            temp_path = f.name
            
        try:
            result = self.runner.invoke(app, ["lint", temp_path])
            self.assertEqual(result.exit_code, 0)
        finally:
            os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
