import unittest
from unittest.mock import patch
import os
import tempfile
import shutil
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typer.testing import CliRunner
from main import app

runner = CliRunner()

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize a git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        # Set git config so commit works
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)

    def tearDown(self):
        # Restore cwd and remove temp dir
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    @patch("main.AIProvider")
    def test_full_commit_flow(self, mock_provider_class):
        """Test full commit flow from staging to git commit using mocked AI."""
        # Setup mock AI
        mock_provider = mock_provider_class.return_value
        mock_provider.execute.return_value = "feat: add user authentication\n\nThis is a mock commit."
        
        # Create and stage a file
        with open("test_file.txt", "w") as f:
            f.write("Hello World")
        subprocess.run(["git", "add", "test_file.txt"], check=True)
        
        # Run sensei commit, simulating "y" to accept the commit
        # By passing --provider echo, we avoid config loading issues, though AIProvider is mocked anyway.
        result = runner.invoke(app, ["commit", "--provider", "echo"], input="y\n")
        
        # Verify CLI output
        self.assertEqual(result.exit_code, 0)
        self.assertIn("feat: add user authentication", result.stdout)
        self.assertIn("Committed!", result.stdout)
        
        # Verify git log to ensure the commit was actually created
        log_result = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True)
        self.assertIn("feat: add user authentication", log_result.stdout)

    @patch("main.AIProvider")
    def test_commit_abort(self, mock_provider_class):
        """Test user aborting the commit message."""
        mock_provider = mock_provider_class.return_value
        mock_provider.execute.return_value = "feat: bad message"
        
        with open("test_file2.txt", "w") as f:
            f.write("Hello World")
        subprocess.run(["git", "add", "test_file2.txt"], check=True)
        
        # Simulate "n" to abort
        result = runner.invoke(app, ["commit"], input="n\n")
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Aborted.", result.stdout)
        
        # Ensure no commits were made
        log_result = subprocess.run(["git", "log"], capture_output=True, text=True)
        self.assertNotEqual(log_result.returncode, 0) # git log fails if there are no commits

if __name__ == "__main__":
    unittest.main()
