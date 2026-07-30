import unittest
from unittest.mock import patch

from git_sensei.git_utils import get_staged_diff_filtered


class TestSmartTruncation(unittest.TestCase):
    @patch("git_sensei.git_utils.get_staged_diff", return_value=None)
    def test_no_diff(self, mock_get_staged_diff):
        diff, meta = get_staged_diff_filtered({}, diff_override=None)
        self.assertIsNone(diff)
        self.assertEqual(meta["skipped"], {})
        self.assertFalse(meta["truncated"])

    def test_skip_lockfile_and_patterns(self):
        raw_diff = (
            "diff --git a/package-lock.json b/package-lock.json\n"
            "index 123..456 100644\n"
            "--- a/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "@@ -1,2 +1,3 @@\n"
            "+some change\n"
            "diff --git a/src/main.py b/src/main.py\n"
            "index 789..012 100644\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-old\n"
            "+new\n"
        )
        config = {
            "truncation": {
                "max_tokens": 1000,
                "strategy": "smart",
                "skip_patterns": ["package-lock.json"]
            }
        }
        diff, meta = get_staged_diff_filtered(config, diff_override=raw_diff)
        self.assertNotIn("package-lock.json", diff)
        self.assertIn("src/main.py", diff)
        self.assertIn("package-lock.json", meta["skipped"])
        self.assertIn("lockfile", meta["skipped"]["package-lock.json"])

    def test_binary_and_minified(self):
        raw_diff = (
            "diff --git a/images/logo.png b/images/logo.png\n"
            "Binary files a/images/logo.png and b/images/logo.png differ\n"
            "diff --git a/dist/bundle.min.js b/dist/bundle.min.js\n"
            "index 123..456 100644\n"
            "--- a/dist/bundle.min.js\n"
            "+++ b/dist/bundle.min.js\n"
            "@@ -1 +1 @@\n"
            "+minified content\n"
        )
        config = {
            "truncation": {
                "max_tokens": 1000,
                "strategy": "smart",
                "skip_patterns": []
            }
        }
        diff, meta = get_staged_diff_filtered(config, diff_override=raw_diff)
        self.assertEqual(diff, "")
        self.assertEqual(meta["skipped"]["images/logo.png"], "binary")
        self.assertEqual(meta["skipped"]["dist/bundle.min.js"], "minified")

    def test_head_truncation(self):
        raw_diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "line 1\n"
            "line 2\n"
            "line 3\n"
            "line 4\n"
        )
        # 1 token = 4 chars. "line 1\n" has 7 chars => ~1.75 tokens.
        # We set max_tokens very low (e.g. 15) to force truncation
        config = {
            "truncation": {
                "max_tokens": 15,
                "strategy": "head",
                "skip_patterns": []
            }
        }
        diff, meta = get_staged_diff_filtered(config, diff_override=raw_diff)
        self.assertTrue(meta["truncated"])
        self.assertEqual(meta["strategy"], "head")
        self.assertIn("line 1", diff)
        self.assertIn("[TRUNCATED]", diff)

    def test_smart_truncation(self):
        raw_diff = (
            "diff --git a/src/small.py b/src/small.py\n"
            "@@ -1 +1 @@\n"
            "+small change\n"
            "diff --git a/src/large.py b/src/large.py\n"
            "@@ -1 +1 @@\n"
            "+large change line 1\n"
            "+large change line 2\n"
            "+large change line 3\n"
            "+large change line 4\n"
            "+large change line 5\n"
        )
        # set token budget such that only small.py and the header of large.py fits
        config = {
            "truncation": {
                "max_tokens": 20,
                "strategy": "smart",
                "skip_patterns": []
            }
        }
        diff, meta = get_staged_diff_filtered(config, diff_override=raw_diff)
        self.assertTrue(meta["truncated"])
        self.assertIn("src/small.py", diff)
        self.assertIn("small change", diff)
        self.assertIn("src/large.py", diff)
        self.assertNotIn("large change line 5", diff)
        self.assertIn("truncated", meta["skipped"]["src/large.py"])

if __name__ == "__main__":
    unittest.main()
