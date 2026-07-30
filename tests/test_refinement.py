import unittest

from git_sensei.main import update_commit_message_header


class TestRefinementAndSelection(unittest.TestCase):
    def test_update_header_no_emoji_no_scope(self):
        msg = "docs: update readme\n\nSome body"
        updated = update_commit_message_header(msg, "feat", False)
        self.assertEqual(updated, "feat: update readme\n\nSome body")

    def test_update_header_with_emoji_and_scope(self):
        msg = "docs(readme): update readme\n\nSome body"
        updated = update_commit_message_header(msg, "feat", True)
        self.assertEqual(updated, "✨ feat(readme): update readme\n\nSome body")

    def test_update_header_existing_emoji_replaced(self):
        msg = "📝 docs(readme): update readme\n\nSome body"
        updated = update_commit_message_header(msg, "fix", True)
        self.assertEqual(updated, "🐛 fix(readme): update readme\n\nSome body")

    def test_update_header_existing_emoji_removed(self):
        msg = "📝 docs(readme): update readme\n\nSome body"
        updated = update_commit_message_header(msg, "fix", False)
        self.assertEqual(updated, "fix(readme): update readme\n\nSome body")

    def test_update_header_non_conventional_fallback(self):
        msg = "just a plain message without formatting"
        updated = update_commit_message_header(msg, "chore", True)
        self.assertEqual(updated, "🔧 chore: just a plain message without formatting")

if __name__ == "__main__":
    unittest.main()
