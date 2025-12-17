import sys
import re
import os

def parse_diff(diff_content):
    """
    Analyzes the diff and returns a list of modified files and hints about the type of changes.
    """
    files = []
    is_fix = False
    is_test = False
    
    # Simple diff parser
    # Looking for lines: diff --git a/path/file b/path/file
    file_pattern = re.compile(r"diff --git a/(.*) b/(.*)")
    
    for line in diff_content.splitlines():
        # Detect files
        match = file_pattern.match(line)
        if match:
            files.append(match.group(1))
        
        # Heuristics for content (search for keywords in added lines)
        if line.startswith("+") and not line.startswith("+++"):
            content_lower = line.lower()
            if "fix" in content_lower or "bug" in content_lower or "error" in content_lower:
                is_fix = True
            if "test" in content_lower:
                is_test = True

    return files, is_fix, is_test

def determine_type(files, is_fix_content):
    """Determines the commit type based on file extensions."""
    if not files:
        return "chore"

    # Priorities
    if is_fix_content:
        return "fix"

    extensions = [os.path.splitext(f)[1] for f in files]
    
    # Map extensions to types
    if any(ext in ['.md', '.txt', '.rst'] for ext in extensions):
        return "docs"
    if any(ext in ['.css', '.scss', '.less', '.styl'] for ext in extensions):
        return "style"
    if any('test' in f.lower() for f in files):
        return "test"
    if any(f in ['.gitignore', 'requirements.txt', 'Dockerfile', 'package.json', '.env.example'] for f in files):
        return "chore"
    if any(ext in ['.py', '.js', '.ts', '.go', '.rs', '.java', '.c', '.cpp'] for ext in extensions):
        return "feat"
    
    return "chore"

def generate_message(diff_content):
    files, is_fix, is_test = parse_diff(diff_content)
    
    if not files:
        return "chore: minor update"

    commit_type = determine_type(files, is_fix)
    
    # Scope: main file name (without path and extension)
    main_file = os.path.basename(files[0])
    scope = os.path.splitext(main_file)[0]
    
    if len(files) > 1:
        scope = f"{scope}+" # Signal that more than one file was changed

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

if __name__ == "__main__":
    # Non-interactive mode: read from stdin, write to stdout
    try:
        # Force UTF-8 encoding for stdin/stdout
        if sys.stdin.encoding.lower() != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')
        if sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
            
        input_diff = sys.stdin.read()
        if not input_diff.strip():
            # Fallback for empty input
            print("chore: empty commit")
        else:
            message = generate_message(input_diff)
            print(message)
            
    except Exception as e:
        # Fallback in case of parsing error
        print(f"chore: manual check required (error: {str(e)})")