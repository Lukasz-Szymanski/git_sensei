import subprocess
import re
import fnmatch
from typing import Optional, List, Tuple


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
        (r'(?:ado|ab#)[/-]?(\d+)', 'AB#{}'), # Azure DevOps
        (r'(?:gh|issue)[/-](\d+)', '#{}'),   # GitHub
        (r'sc[/-](\d+)', 'sc-{}'),          # Shortcut
        (r'(?:^|/)#(\d+)', '#{}'),          # GitHub/GitLab
        (r'([a-z]{2,}-\d+)', 'UPPER'),      # Jira/Linear
        (r'[/-](\d+)[/-]', '#{}'),          # feature/1-description -> #1
        (r'[/-](\d+)$', '#{}'),             # feature/1 -> #1
    ]

    for pattern, format_str in patterns:
        match = re.search(pattern, branch_name, re.IGNORECASE)
        if match:
            if format_str == 'UPPER':
                return match.group(1).upper()
            if format_str:
                return format_str.format(*match.groups())
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


def get_staged_files() -> List[str]:
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--name-only"],
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def get_amend_files() -> List[str]:
    """Get list of files changed in last commit + staged."""
    try:
        # Check if HEAD~1 exists
        subprocess.check_call(["git", "rev-parse", "HEAD~1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        diff_cmd = ["git", "diff", "HEAD~1", "--staged", "--name-only"]
    except subprocess.CalledProcessError:
        diff_cmd = ["git", "diff", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "--staged", "--name-only"]
        
    try:
        result = subprocess.run(
            diff_cmd,
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def get_git_context(config: Optional[dict] = None) -> dict:
    """
    Gather full git context for AI prompt.

    Returns dict with:
        - branch: current branch name
        - issue_id: extracted issue ID or None
        - branch_type: feat/fix/etc or None
        - scope: detected monorepo scope or None
        - is_pushed: whether branch exists on remote
        - commits_ahead: number of commits ahead of main
        - context_summary: human-readable summary
    """
    branch = get_current_branch()
    issue_id = extract_issue_id(branch)
    branch_type = extract_branch_type(branch)
    is_pushed = is_branch_pushed(branch)
    commits_ahead = get_commits_ahead_of_main()

    # Detect monorepo scope
    scope = None
    if config:
        monorepo_cfg = config.get("monorepo", {})
        staged_files = get_staged_files()
        if not staged_files:
            staged_files = get_amend_files()
        scope = detect_monorepo_scope(staged_files, monorepo_cfg)

    # Build context summary
    summary_parts = []

    if branch in ['main', 'master']:
        summary_parts.append("Direct commit to main branch")
    else:
        if branch_type:
            summary_parts.append(f"Type: {branch_type}")
        if scope:
            summary_parts.append(f"Scope: {scope}")
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
        'scope': scope,
        'is_pushed': is_pushed,
        'commits_ahead': commits_ahead,
        'context_summary': '; '.join(summary_parts) if summary_parts else None,
    }

def get_amend_diff() -> Optional[str]:
    """Get diff for amending the last commit (includes staged changes)."""
    try:
        # Check if HEAD~1 exists
        subprocess.check_call(["git", "rev-parse", "HEAD~1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        diff_cmd = ["git", "diff", "HEAD~1", "--staged"]
    except subprocess.CalledProcessError:
        # Initial commit fallback (diff against empty tree)
        diff_cmd = ["git", "diff", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "--staged"]
        
    result = subprocess.run(
        diff_cmd,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout
    return None

def amend_commit(message: str) -> bool:
    """Amend the last git commit with the given message."""
    try:
        subprocess.run(["git", "commit", "--amend", "-m", message], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def get_last_commit_message() -> Optional[str]:
    """Get the message of the last commit."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def is_commit_pushed(commit: str = "HEAD") -> bool:
    """Check if a specific commit is pushed to any remote branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "-r", "--contains", commit],
            capture_output=True, text=True, encoding='utf-8'
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def get_recent_commits(limit: int = 3, start_ref: str = "HEAD") -> List[str]:
    """Fetch messages of the last limit commits starting from start_ref, filtering out merges."""
    if limit <= 0:
        return []
    try:
        result = subprocess.run(
            ["git", "log", start_ref, f"-{limit}", "--no-merges", "--format=%B===COMMIT_MSG_DELIMITER==="],
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        output = result.stdout
        parts = output.split("===COMMIT_MSG_DELIMITER===")
        commits = []
        for part in parts:
            stripped = part.strip()
            if stripped:
                commits.append(stripped)
        return commits
    except Exception:
        return []


def get_staged_diff_filtered(config: dict, diff_override: Optional[str] = None) -> Tuple[Optional[str], dict]:
    """
    Get staged changes diff, filtered and truncated according to config.
    Returns:
        Tuple[filtered_diff_str, metadata_dict]
    """
    diff = diff_override if diff_override is not None else get_staged_diff()
    if not diff:
        return None, {"skipped": {}, "truncated": False, "strategy": None}

    truncation_cfg = config.get("truncation", {})
    max_tokens = truncation_cfg.get("max_tokens", 4000)
    strategy = truncation_cfg.get("strategy", "smart")
    skip_patterns = truncation_cfg.get("skip_patterns", [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
        "*.min.js", "*.min.css", "*.map", "dist/*", "build/*"
    ])

    # Helper function to match pattern recursively or by prefix
    def matches_pattern(filepath: str, pattern: str) -> bool:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        if pattern.endswith("/*"):
            dir_prefix = pattern[:-2]
            if filepath.startswith(dir_prefix + "/"):
                return True
        if pattern.endswith("/"):
            if filepath.startswith(pattern):
                return True
        return False

    # Split diff into files
    file_diffs = re.split(r'(?=^diff --git )', diff, flags=re.MULTILINE)
    file_diffs = [fd for fd in file_diffs if fd.strip()]

    skipped_files = {}
    included_chunks = []
    truncated = False

    for fd in file_diffs:
        # Extract filename
        first_line = fd.split('\n')[0]
        match = re.search(r'^diff --git a/(.*?) b/(.*?)$', first_line)
        filename = ""
        if match:
            b_path = match.group(2)
            filename = match.group(1) if b_path in ("/dev/null", "dev/null") else b_path
        
        if not filename:
            included_chunks.append((fd, len(fd) // 4, ""))
            continue

        # Check binary
        if "Binary files " in fd and " differ" in fd:
            skipped_files[filename] = "binary"
            continue

        # Check minified
        if filename.endswith(('.min.js', '.min.css', '.map')):
            skipped_files[filename] = "minified"
            continue

        # Check pattern match
        matched_pattern = None
        for pat in skip_patterns:
            if matches_pattern(filename, pat):
                matched_pattern = pat
                break
        
        if matched_pattern:
            # Check if it is a lockfile
            if filename in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"):
                lines_count = len(fd.splitlines())
                skipped_files[filename] = f"lockfile ({lines_count:,} lines)"
            else:
                skipped_files[filename] = "skipped"
            continue

        # Otherwise, keep it
        tokens = len(fd) // 4
        included_chunks.append((fd, tokens, filename))

    # Calculate total tokens
    total_tokens = sum(t[1] for t in included_chunks)

    filtered_diff = ""
    # Truncation logic if exceeding max_tokens
    if total_tokens > max_tokens:
        truncated = True
        if strategy == "head":
            # Combine all diffs and keep head lines up to max_tokens
            combined_diff = "\n".join(t[0] for t in included_chunks)
            lines = combined_diff.splitlines()
            current_tokens = 0
            selected_lines = []
            for line in lines:
                line_tokens = len(line) // 4 + 1
                if current_tokens + line_tokens > max_tokens:
                    break
                selected_lines.append(line)
                current_tokens += line_tokens
            filtered_diff = "\n".join(selected_lines) + "\n... [TRUNCATED] ..."
        elif strategy == "tail":
            combined_diff = "\n".join(t[0] for t in included_chunks)
            lines = combined_diff.splitlines()
            current_tokens = 0
            selected_lines = []
            for line in reversed(lines):
                line_tokens = len(line) // 4 + 1
                if current_tokens + line_tokens > max_tokens:
                    break
                selected_lines.insert(0, line)
                current_tokens += line_tokens
            filtered_diff = "... [TRUNCATED] ...\n" + "\n".join(selected_lines)
        elif strategy == "sample":
            # Keep first half of token budget from start, second half from end
            combined_diff = "\n".join(t[0] for t in included_chunks)
            lines = combined_diff.splitlines()
            half_budget = max_tokens // 2
            
            # Head lines
            head_lines = []
            current_tokens = 0
            head_idx = 0
            for i, line in enumerate(lines):
                line_tokens = len(line) // 4 + 1
                if current_tokens + line_tokens > half_budget:
                    head_idx = i
                    break
                head_lines.append(line)
                current_tokens += line_tokens
            
            # Tail lines
            tail_lines = []
            current_tokens = 0
            for line in reversed(lines[head_idx:]):
                line_tokens = len(line) // 4 + 1
                if current_tokens + line_tokens > half_budget:
                    break
                tail_lines.insert(0, line)
                current_tokens += line_tokens
            
            filtered_diff = "\n".join(head_lines) + "\n... [TRUNCATED] ...\n" + "\n".join(tail_lines)
        else: # "smart"
            # Sort files by diff size (ascending) to keep as many complete files as possible
            included_chunks_sorted = sorted([t for t in included_chunks if t[2]], key=lambda x: x[1])
            allowed_files = set()
            current_tokens = 0
            
            # Add files without filenames (e.g. general diff chunks if any) first or keep them
            general_chunks = [t for t in included_chunks if not t[2]]
            for gc in general_chunks:
                current_tokens += gc[1]
                
            for fd, tokens, filename in included_chunks_sorted:
                if current_tokens + tokens <= max_tokens:
                    allowed_files.add(filename)
                    current_tokens += tokens
                else:
                    break
            
            # For files that didn't fit, we summarize them
            diff_parts = []
            for fd, tokens, filename in included_chunks:
                if not filename or filename in allowed_files:
                    diff_parts.append(fd)
                else:
                    # Summarize: Keep just the diff header (first few lines up to first @@)
                    header_lines = []
                    for line in fd.splitlines():
                        header_lines.append(line)
                        if line.startswith("@@"):
                            break
                    diff_parts.append("\n".join(header_lines) + "\n... [DIFF TRUNCATED FOR THIS FILE] ...")
                    skipped_files[filename] = "truncated"
            filtered_diff = "\n".join(diff_parts)
    else:
        filtered_diff = "\n".join(t[0] for t in included_chunks)

    return filtered_diff, {
        "skipped": skipped_files,
        "truncated": truncated,
        "strategy": strategy if truncated else None
    }


def detect_monorepo_scope(changed_files: List[str], monorepo_config: dict) -> Optional[str]:
    """
    Detect commit scope from changed files in a monorepo setting.
    """
    if not monorepo_config or not monorepo_config.get("enabled", False):
        return None

    if not changed_files:
        return None

    custom_scopes = monorepo_config.get("scopes", {})
    # Sort custom scopes keys by length descending to match deepest first
    sorted_custom_keys = sorted(custom_scopes.keys(), key=len, reverse=True)

    # Determine packages directories
    packages_dirs = []
    p_dirs = monorepo_config.get("packages_dirs")
    if isinstance(p_dirs, list):
        packages_dirs.extend(p_dirs)
    p_dir = monorepo_config.get("packages_dir")
    if isinstance(p_dir, str) and p_dir:
        packages_dirs.append(p_dir)
    if not p_dirs and not p_dir:
        packages_dirs.extend(["packages", "apps", "libs"])

    # Clean package dirs to end with /
    packages_prefixes = []
    for d in packages_dirs:
        d_clean = d.strip("/")
        if d_clean:
            packages_prefixes.append(d_clean + "/")

    scope_counts = {}

    for filepath in changed_files:
        matched_scope = None
        
        # 1. Try custom scopes first (deepest match wins)
        for key in sorted_custom_keys:
            # Check prefix or glob match
            if filepath.startswith(key.strip("/") + "/") or filepath == key or fnmatch.fnmatch(filepath, key):
                matched_scope = custom_scopes[key]
                break

        # 2. Try inferring from monorepo directories
        if not matched_scope:
            for prefix in packages_prefixes:
                if filepath.startswith(prefix):
                    # Extract the package name (the segment immediately following prefix)
                    remaining = filepath[len(prefix):]
                    parts = remaining.split("/")
                    if parts and parts[0]:
                        matched_scope = parts[0]
                        break

        if matched_scope:
            scope_counts[matched_scope] = scope_counts.get(matched_scope, 0) + 1

    if not scope_counts:
        return None

    # Find the scope with the maximum count
    max_count = max(scope_counts.values())
    candidates = [scope for scope, count in scope_counts.items() if count == max_count]

    # If there is a tie or it's ambiguous, return None (unclear)
    if len(candidates) == 1:
        return candidates[0]
    return None




