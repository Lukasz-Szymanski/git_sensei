"""Unit tests for Changelog generator."""
from git_sensei.core.changelog import (
    categorize_commits,
    generate_local_changelog,
    update_changelog_file
)
import tempfile
import os

def test_categorize_commits():
    commits = [
        {"hash": "abc1234", "subject": "feat(cli): add changelog command"},
        {"hash": "def5678", "subject": "fix: resolve timeout crash"},
        {"hash": "1112223", "subject": "docs: update readme with changelog"},
        {"hash": "4445556", "subject": "random commit without convention"},
    ]
    categorized = categorize_commits(commits)
    assert len(categorized["feat"]) == 1
    assert categorized["feat"][0]["hash"] == "abc1234"
    assert len(categorized["fix"]) == 1
    assert len(categorized["docs"]) == 1
    assert len(categorized["other"]) == 1

def test_generate_local_changelog():
    categories = {
        "feat": [{"hash": "a1b2", "subject": "feat: cool feature"}],
        "fix": [{"hash": "c3d4", "subject": "fix: critical bug"}],
        "perf": [],
        "refactor": [],
        "docs": [],
        "ci": [],
        "chore": [],
        "other": []
    }
    log = generate_local_changelog("v0.16.0", categories)
    assert "## [v0.16.0]" in log
    assert "### 🚀 Features" in log
    assert "- feat: cool feature (a1b2)" in log
    assert "### 🐛 Bug Fixes" in log
    assert "- fix: critical bug (c3d4)" in log

def test_update_changelog_file_existing():
    initial = """# Changelog

All notable changes to this project will be documented in this file.

## [v0.15.1] - 2026-07-30
- Initial fix
"""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".md") as tmp:
        tmp.write(initial)
        tmp_path = tmp.name

    try:
        new_entry = "## [v0.16.0] - 2026-11-10\n- New feature"
        update_changelog_file(tmp_path, new_entry)
        with open(tmp_path, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "## [v0.16.0] - 2026-11-10" in updated
        assert "## [v0.15.1] - 2026-07-30" in updated
        # New entry should be inserted above older entry
        assert updated.index("v0.16.0") < updated.index("v0.15.1")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
