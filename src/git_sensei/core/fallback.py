"""Heuristic fallback commit message generator for offline use."""
import os
import re
from typing import List, Tuple


# File extension to commit type mapping
_DOC_EXTENSIONS = {'.md', '.txt', '.rst'}
_STYLE_EXTENSIONS = {'.css', '.scss', '.less', '.styl'}
_CODE_EXTENSIONS = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.c', '.cpp'}
_CHORE_FILES = {'.gitignore', 'requirements.txt', 'Dockerfile', 'package.json', '.env.example'}


def parse_diff(diff_content: str) -> Tuple[List[str], bool, bool]:
    """
    Analyzes the diff and returns a list of modified files and hints about the type of changes.
    
    Returns:
        Tuple of (files, is_fix, is_test)
    """
    files: List[str] = []
    is_fix = False
    is_test = False
    
    file_pattern = re.compile(r"diff --git a/(.*) b/(.*)")
    
    for line in diff_content.splitlines():
        match = file_pattern.match(line)
        if match:
            files.append(match.group(1))
        
        if line.startswith("+") and not line.startswith("+++"):
            content_lower = line.lower()
            if "fix" in content_lower or "bug" in content_lower or "error" in content_lower:
                is_fix = True
            if "test" in content_lower:
                is_test = True

    return files, is_fix, is_test


def determine_type(files: List[str], is_fix_content: bool) -> str:
    """Determines the commit type based on file extensions."""
    if not files:
        return "chore"

    if is_fix_content:
        return "fix"

    extensions = [os.path.splitext(f)[1] for f in files]
    
    if any(ext in _DOC_EXTENSIONS for ext in extensions):
        return "docs"
    if any(ext in _STYLE_EXTENSIONS for ext in extensions):
        return "style"
    if any('test' in f.lower() for f in files):
        return "test"
    if any(f in _CHORE_FILES for f in files):
        return "chore"
    if any(ext in _CODE_EXTENSIONS for ext in extensions):
        return "feat"
    
    return "chore"


def generate_fallback_message(diff_content: str) -> str:
    """Generate a commit message using local heuristics (no AI required).
    
    This is a fallback for when AI providers are unavailable.
    """
    files, is_fix, is_test = parse_diff(diff_content)
    
    if not files:
        return "chore: minor update"

    commit_type = determine_type(files, is_fix)
    
    # Scope: main file name (without path and extension)
    main_file = os.path.basename(files[0])
    scope = os.path.splitext(main_file)[0]
    
    if len(files) > 1:
        scope = f"{scope}+"

    # Description
    action = "fix" if commit_type == "fix" else "update"
    if commit_type == "feat":
        action = "implement"
    elif commit_type == "docs":
        action = "document"
    elif commit_type == "test":
        action = "add tests for"

    description = f"{action} logic in {main_file}"
    if len(files) > 1:
         description += f" and {len(files)-1} other files"

    return f"{commit_type}({scope}): {description}"
