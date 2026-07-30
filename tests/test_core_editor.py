import unittest
from unittest.mock import mock_open, patch

from git_sensei.core.editor import edit_in_editor, get_editor


class TestCoreEditor(unittest.TestCase):
    @patch("os.environ.get")
    def test_get_editor_from_env(self, mock_env_get):
        mock_env_get.side_effect = lambda k: "vim" if k == "VISUAL" else None
        self.assertEqual(get_editor(), "vim")
        
    @patch("os.environ.get")
    @patch("subprocess.run")
    def test_get_editor_from_git_config(self, mock_run, mock_env_get):
        mock_env_get.return_value = None
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "code --wait\n"
        self.assertEqual(get_editor(), "code --wait")

    @patch("git_sensei.core.editor.get_editor")
    @patch("tempfile.NamedTemporaryFile")
    @patch("subprocess.run")
    @patch("os.unlink")
    def test_edit_in_editor_success(self, mock_unlink, mock_run, mock_temp, mock_get_editor):
        mock_get_editor.return_value = "nano"
        
        # Setup mock temporary file
        mock_file = mock_temp.return_value.__enter__.return_value
        mock_file.name = "/tmp/fake_commit.txt"
        
        # Setup mock reading of the edited file
        edited_content = "feat(auth): add login\n\nSome body\n# this is a comment"
        with patch("builtins.open", mock_open(read_data=edited_content)):
            result = edit_in_editor("initial message")
            
        self.assertEqual(result, "feat(auth): add login\n\nSome body")
        mock_run.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/fake_commit.txt")

    @patch("git_sensei.core.editor.get_editor")
    def test_edit_in_editor_no_editor(self, mock_get_editor):
        mock_get_editor.return_value = None
        self.assertIsNone(edit_in_editor("test"))
