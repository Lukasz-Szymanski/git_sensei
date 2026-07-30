import unittest
from git_sensei.git_utils import split_staged_diff

class TestAtomicCommitSplitter(unittest.TestCase):
    def test_split_staged_diff_heuristic(self):
        raw_diff = (
            "diff --git a/docs/README.md b/docs/README.md\n"
            "index 123..456 100644\n"
            "--- a/docs/README.md\n"
            "+++ b/docs/README.md\n"
            "@@ -1 +1 @@\n"
            "+new doc line\n"
            "diff --git a/packages/auth/index.js b/packages/auth/index.js\n"
            "index 123..456 100644\n"
            "--- a/packages/auth/index.js\n"
            "+++ b/packages/auth/index.js\n"
            "@@ -1 +1 @@\n"
            "+auth code\n"
            "diff --git a/tests/test_auth.py b/tests/test_auth.py\n"
            "index 123..456 100644\n"
            "--- a/tests/test_auth.py\n"
            "+++ b/tests/test_auth.py\n"
            "@@ -1 +1 @@\n"
            "+test code\n"
        )
        groups = split_staged_diff(raw_diff)
        self.assertEqual(len(groups), 3)
        
        # Verify groups properties
        docs_group = next(g for g in groups if "docs/README.md" in g["files"])
        self.assertEqual(docs_group["suggested_message"], "docs: update documentation")
        
        auth_group = next(g for g in groups if "packages/auth/index.js" in g["files"])
        self.assertEqual(auth_group["suggested_message"], "feat(auth): update auth")
        
        test_group = next(g for g in groups if "tests/test_auth.py" in g["files"])
        self.assertEqual(test_group["suggested_message"], "test: update unit tests")

if __name__ == "__main__":
    unittest.main()
