import unittest

from git_sensei.core.fallback import (
    determine_type,
    generate_fallback_message,
    parse_diff,
)


class TestCoreFallback(unittest.TestCase):
    def test_parse_diff(self):
        diff = "diff --git a/src/main.py b/src/main.py\n+++ b/src/main.py\n+def fix_bug(): pass"
        files, is_fix, is_test = parse_diff(diff)
        self.assertEqual(files, ["src/main.py"])
        self.assertTrue(is_fix)
        self.assertFalse(is_test)

    def test_determine_type(self):
        self.assertEqual(determine_type([], False), "chore")
        self.assertEqual(determine_type(["app.py"], True), "fix")
        self.assertEqual(determine_type(["README.md"], False), "docs")
        self.assertEqual(determine_type(["style.css"], False), "style")
        self.assertEqual(determine_type(["test_app.py"], False), "test")
        self.assertEqual(determine_type(["main.go"], False), "feat")

    def test_generate_fallback_message(self):
        diff = "diff --git a/src/main.py b/src/main.py\n+++ b/src/main.py\n+def new_feature(): pass"
        msg = generate_fallback_message(diff)
        self.assertTrue(msg.startswith("feat(main): implement logic in main.py"))
        
        diff_fix = "diff --git a/app.js b/app.js\n+++ b/app.js\n+ // fix error"
        msg_fix = generate_fallback_message(diff_fix)
        self.assertTrue(msg_fix.startswith("fix(app): fix logic in app.js"))
