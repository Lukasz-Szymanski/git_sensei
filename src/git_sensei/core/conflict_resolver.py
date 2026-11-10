"""Smart Git Merge Conflict Resolver for Git-Sensei."""
from typing import List, Dict, Any, Optional
import os
import re
import subprocess
from rich.console import Console

CONFLICT_SYSTEM_PROMPT = """You are an expert software engineer specializing in git conflict resolution.
You will be provided with a file content that contains standard git conflict markers:
<<<<<<< HEAD (current changes)
...
=======
...
>>>>>>> branch/ref (incoming changes)

Your task:
1. Carefully analyze both sides of the conflict and surrounding code context.
2. Resolve the conflict by intelligently combining both changes without breaking logic, syntax, or losing intentional updates from either side.
3. Cleanly remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
4. Output ONLY the fully resolved, clean file content. Do NOT include markdown code fences (```) or conversational commentary.
"""

def get_conflicted_files() -> List[str]:
    """Return a list of unmerged/conflicted filepaths in the repository."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            capture_output=True,
            text=True,
            check=True
        )
        files = [f.strip() for f in res.stdout.strip().splitlines() if f.strip()]
        return files
    except Exception:
        return []

def extract_conflict_sections(content: str) -> List[Dict[str, str]]:
    """Find conflict blocks in file content for preview."""
    pattern = re.compile(r"<{7}[^\n]*\n(.*?)\n={7}\n(.*?)\n>{7}[^\n]*", re.DOTALL)
    conflicts = []
    for match in pattern.finditer(content):
        conflicts.append({
            "ours": match.group(1),
            "theirs": match.group(2)
        })
    return conflicts

def clean_resolved_content(raw_response: str) -> str:
    """Strip any unwanted markdown code fences returned by AI."""
    text = raw_response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first fence line (e.g. ```python or ```)
        if len(lines) > 1:
            lines = lines[1:]
        # drop last fence line if ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text

def resolve_file_conflict(
    filepath: str,
    ai_provider: Any,
    console: Optional[Console] = None
) -> Dict[str, Any]:
    """Resolve conflicts in a single file using AI."""
    if console is None:
        console = Console()

    if not os.path.exists(filepath):
        return {"success": False, "error": f"File '{filepath}' not found."}

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    conflicts = extract_conflict_sections(content)
    if not conflicts:
        return {"success": False, "error": f"No conflict markers found in '{filepath}'."}

    prompt = (
        f"{CONFLICT_SYSTEM_PROMPT}\n\n"
        f"File: {filepath}\n"
        f"Total conflict blocks: {len(conflicts)}\n"
        f"--- CONFLICTING FILE CONTENT START ---\n"
        f"{content}\n"
        f"--- CONFLICTING FILE CONTENT END ---"
    )

    raw_resolution = ai_provider.execute(content, prompt)
    if not raw_resolution:
        return {"success": False, "error": "AI provider returned empty resolution."}

    resolved_content = clean_resolved_content(raw_resolution)

    # Check if markers still remain in resolution
    remaining_markers = bool(re.search(r"<{7}|={7}|>{7}", resolved_content))

    return {
        "success": True,
        "filepath": filepath,
        "conflicts_count": len(conflicts),
        "original_content": content,
        "resolved_content": resolved_content,
        "has_remaining_markers": remaining_markers
    }
