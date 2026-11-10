"""Changelog Generator module for Git-Sensei."""
from typing import List, Dict, Optional
import subprocess
import re
from datetime import datetime

CHANGELOG_SYSTEM_PROMPT = """You are an expert release manager and technical writer.
You will be provided with a raw list of git commits since the last release, categorized by commit type.

Your task:
Generate a professional, human-readable release notes / changelog entry.

Guidelines:
1. Highlight significant features and fixes clearly for end users and developers.
2. Group entries into standard markdown sections:
   - 🚀 Features
   - 🐛 Bug Fixes
   - ⚡ Performance Improvements
   - 🛠️ Maintenance & Refactoring
   - ⚠️ Breaking Changes (if any)
3. For each bullet point, write a concise explanation (include commit hash/scope when relevant).
4. Output ONLY valid markdown. Do not wrap output in ```markdown ``` fences.
"""

def get_latest_git_tag() -> Optional[str]:
    """Retrieve the latest git tag."""
    try:
        res = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True
        )
        tag = res.stdout.strip()
        return tag if tag else None
    except Exception:
        return None

def get_commits_since(tag: Optional[str] = None) -> List[Dict[str, str]]:
    """Retrieve list of commits since a given git tag (or all if None)."""
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    try:
        # format: hash|subject|body
        res = subprocess.run(
            ["git", "log", rev_range, "--format=%h|%s"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        commits = []
        for line in lines:
            parts = line.split("|", 1)
            hash_str = parts[0]
            subject = parts[1] if len(parts) > 1 else ""
            commits.append({"hash": hash_str, "subject": subject})
        return commits
    except Exception:
        return []

def categorize_commits(commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize commits by conventional commit prefix."""
    categories: Dict[str, List[Dict[str, str]]] = {
        "feat": [],
        "fix": [],
        "perf": [],
        "refactor": [],
        "docs": [],
        "ci": [],
        "chore": [],
        "other": []
    }

    pattern = re.compile(r"^(\w+)(?:\(([^)]+)\))?!?: (.+)$")

    for commit in commits:
        subj = commit["subject"]
        match = pattern.match(subj)
        if match:
            c_type = match.group(1).lower()
            if c_type in categories:
                categories[c_type].append(commit)
            else:
                categories["other"].append(commit)
        else:
            categories["other"].append(commit)

    return categories

def generate_local_changelog(version: str, categories: Dict[str, List[Dict[str, str]]]) -> str:
    """Fallback generator producing markdown without AI."""
    today = datetime.now().strftime("%Y-%m-%d")
    out = [f"## [{version}] - {today}\n"]

    section_titles = {
        "feat": "### 🚀 Features",
        "fix": "### 🐛 Bug Fixes",
        "perf": "### ⚡ Performance Improvements",
        "refactor": "### 🛠️ Refactoring",
        "docs": "### 📚 Documentation",
        "ci": "### 🤖 CI/CD & Build",
        "chore": "### 🧹 Chores",
        "other": "### 📌 Other Changes"
    }

    for key, title in section_titles.items():
        items = categories.get(key, [])
        if items:
            out.append(f"{title}")
            for it in items:
                out.append(f"- {it['subject']} ({it['hash']})")
            out.append("")

    return "\n".join(out).strip()

def build_changelog_prompt(version: str, prev_tag: Optional[str], commits: List[Dict[str, str]]) -> str:
    """Build prompt for AI release note generator."""
    lines = [f"- {c['hash']}: {c['subject']}" for c in commits]
    commits_text = "\n".join(lines)

    return (
        f"{CHANGELOG_SYSTEM_PROMPT}\n\n"
        f"Version: {version}\n"
        f"Previous release tag: {prev_tag or 'First release'}\n"
        f"Commits to include ({len(commits)}):\n"
        f"{commits_text}\n"
    )

def update_changelog_file(filepath: str, new_entry: str) -> None:
    """Prepend or append new entry into CHANGELOG.md cleanly."""
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

    content = ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = header

    if content.startswith("# Changelog"):
        # Insert after the main header
        lines = content.splitlines(keepends=True)
        idx = 0
        for i, line_text in enumerate(lines):
            if line_text.startswith("## "):
                idx = i
                break
        if idx > 0:
            new_content = "".join(lines[:idx]) + new_entry + "\n\n" + "".join(lines[idx:])
        else:
            new_content = content.rstrip() + "\n\n" + new_entry + "\n"
    else:
        new_content = header + new_entry + "\n\n" + content

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
