import unittest
from git_utils import detect_monorepo_scope

class TestMonorepoScope(unittest.TestCase):
    def test_disabled(self):
        config = {"enabled": False}
        files = ["packages/auth/index.js"]
        self.assertIsNone(detect_monorepo_scope(files, config))

    def test_infer_from_default_dirs(self):
        config = {"enabled": True}
        self.assertEqual(detect_monorepo_scope(["packages/auth/index.js"], config), "auth")
        self.assertEqual(detect_monorepo_scope(["apps/web/main.tsx"], config), "web")
        self.assertEqual(detect_monorepo_scope(["libs/shared/utils.py"], config), "shared")

    def test_custom_scopes_exact_and_glob(self):
        config = {
            "enabled": True,
            "scopes": {
                "packages/auth": "auth-service",
                "src/components/*.tsx": "ui",
                "src/helpers": "utils"
            }
        }
        self.assertEqual(detect_monorepo_scope(["packages/auth/index.js"], config), "auth-service")
        self.assertEqual(detect_monorepo_scope(["src/components/Button.tsx"], config), "ui")
        self.assertEqual(detect_monorepo_scope(["src/helpers/date.py"], config), "utils")

    def test_deepest_match(self):
        config = {
            "enabled": True,
            "scopes": {
                "packages/core": "core",
                "packages/core/auth": "auth"
            }
        }
        self.assertEqual(detect_monorepo_scope(["packages/core/auth/index.js"], config), "auth")
        self.assertEqual(detect_monorepo_scope(["packages/core/other/index.js"], config), "core")

    def test_multiple_files_majority_wins(self):
        config = {"enabled": True}
        files = [
            "packages/auth/index.js",
            "packages/auth/tests.js",
            "packages/payment/index.js"
        ]
        self.assertEqual(detect_monorepo_scope(files, config), "auth")

    def test_multiple_files_tie_returns_none(self):
        config = {"enabled": True}
        files = [
            "packages/auth/index.js",
            "packages/payment/index.js"
        ]
        self.assertIsNone(detect_monorepo_scope(files, config))

    def test_root_files_fallback(self):
        config = {"enabled": True}
        self.assertIsNone(detect_monorepo_scope(["README.md", "package.json"], config))

if __name__ == "__main__":
    unittest.main()
