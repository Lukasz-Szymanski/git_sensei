import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_utils import extract_issue_id


class TestExtractIssueId(unittest.TestCase):
    """Tests for extract_issue_id function."""

    # Jira/Linear
    def test_jira_standard(self):
        self.assertEqual(extract_issue_id("feature/PROJ-123-add-login"), "PROJ-123")

    def test_jira_at_start(self):
        self.assertEqual(extract_issue_id("JIRA-456-fix-bug"), "JIRA-456")

    def test_linear(self):
        self.assertEqual(extract_issue_id("feature/LIN-789-new-feature"), "LIN-789")

    # GitHub/GitLab
    def test_github_hash(self):
        self.assertEqual(extract_issue_id("feature/#123-fix"), "#123")

    def test_github_issue_dash(self):
        self.assertEqual(extract_issue_id("issue-456-bug"), "#456")

    def test_github_issue_slash(self):
        self.assertEqual(extract_issue_id("issue/789"), "#789")

    # Azure DevOps
    def test_azure_devops(self):
        self.assertEqual(extract_issue_id("feature/AB#123-task"), "AB#123")

    # Shortcut
    def test_shortcut(self):
        self.assertEqual(extract_issue_id("feature/sc-456-story"), "sc-456")

    # No match
    def test_main_branch(self):
        self.assertIsNone(extract_issue_id("main"))

    def test_feature_no_id(self):
        self.assertIsNone(extract_issue_id("feature/add-dark-mode"))

    def test_multiple_ids_first(self):
        self.assertEqual(extract_issue_id("feature/PROJ-123-and-PROJ-456"), "PROJ-123")


if __name__ == "__main__":
    unittest.main()
