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
        (r'[/-](\d+)[/-]', '#{}'),          # feature/1-description -> #1
        (r'[/-](\d+)$', '#{}'),             # feature/1 -> #1
    ]

    for pattern, format_str in patterns:
        match = re.search(pattern, branch_name, re.IGNORECASE)
        if match:
            if format_str:
                return format_str.format(match.group(1))
            return match.group(1)

    return None


def extract_branch_type(branch_name: str) -> Optional[str]:
    """
    Extract work type from branch prefix.

    Returns: feat, fix, hotfix, refactor, docs, chore, or None
    """
    prefix_map = {
        'feature': 'feat',
        'feat': 'feat',
        'fix': 'fix',
        'bugfix': 'fix',
        'hotfix': 'hotfix',
        'refactor': 'refactor',
        'docs': 'docs',
        'chore': 'chore',
        'test': 'test',
        'ci': 'ci',
    }

    match = re.match(r'^([a-z]+)[/-]', branch_name, re.IGNORECASE)
    if match:
        prefix = match.group(1).lower()
        return prefix_map.get(prefix)

    return None


def is_branch_pushed(branch_name: str) -> bool:
    """Check if branch exists on remote origin."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch_name],
        capture_output=True, text=True, encoding='utf-8'
    )
    return bool(result.stdout.strip())


def get_commits_ahead_of_main() -> int:
    """Count commits ahead of main/master branch."""
    for main_branch in ['main', 'master']:
        result = subprocess.run(
            ["git", "rev-list", f"{main_branch}..HEAD", "--count"],
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    return 0


def get_git_context() -> dict:
    """
    Gather full git context for AI prompt.

    Returns dict with:
        - branch: current branch name
        - issue_id: extracted issue ID or None
        - branch_type: feat/fix/etc or None
        - is_pushed: whether branch exists on remote
        - commits_ahead: number of commits ahead of main
        - context_summary: human-readable summary
    """
    branch = get_current_branch()
    issue_id = extract_issue_id(branch)
    branch_type = extract_branch_type(branch)
    is_pushed = is_branch_pushed(branch)
    commits_ahead = get_commits_ahead_of_main()

    # Build context summary
    summary_parts = []

    if branch in ['main', 'master']:
        summary_parts.append("Direct commit to main branch")
    else:
        if branch_type:
            summary_parts.append(f"Type: {branch_type}")
        if issue_id:
            summary_parts.append(f"Closes issue {issue_id}")
        if not is_pushed:
            summary_parts.append("New branch (not yet pushed)")
        elif commits_ahead > 0:
            summary_parts.append(f"{commits_ahead} commit(s) ahead of main")

    return {
        'branch': branch,
        'issue_id': issue_id,
        'branch_type': branch_type,
        'is_pushed': is_pushed,
        'commits_ahead': commits_ahead,
        'context_summary': '; '.join(summary_parts) if summary_parts else None,
    }
