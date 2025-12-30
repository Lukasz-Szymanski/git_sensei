"""Git utilities for sensei."""
import subprocess
import re
from typing import Optional


def get_current_branch() -> str:
    """Get current git branch name."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()


def get_staged_diff() -> Optional[str]:
    """Get staged changes diff. Returns None if no staged changes."""
    try:
        subprocess.check_call(["git", "diff", "--staged", "--quiet"])
        return None  # No staged changes
    except subprocess.CalledProcessError:
        pass

    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout


def create_commit(message: str) -> bool:
    """Create a git commit with the given message."""
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def extract_issue_id(branch_name: str) -> Optional[str]:
    """
    Extract issue ID from branch name.

    Supports: Jira (PROJ-123), GitHub (#123), Azure DevOps (AB#123),
    Linear (LIN-123), Shortcut (sc-123)
    """
    patterns = [
        (r'(AB#\d+)', None),                # Azure DevOps
        (r'issue[/-](\d+)', '#{}'),         # issue-123 -> #123
        (r'sc[/-](\d+)', 'sc-{}'),          # Shortcut
        (r'(?:^|/)#(\d+)', '#{}'),          # GitHub/GitLab
        (r'([A-Z]{2,}-\d+)', None),         # Jira/Linear
    ]

    for pattern, format_str in patterns:
        match = re.search(pattern, branch_name, re.IGNORECASE)
        if match:
            if format_str:
                return format_str.format(match.group(1))
            return match.group(1)

    return None
