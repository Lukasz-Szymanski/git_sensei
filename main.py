import subprocess
import shutil
import sys
import typer
import os
import re

app = typer.Typer()

# Conventional Commits Regex
CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./\+]+\))?: .+$"

# System prompt optimized for CLI pipes
SYSTEM_PROMPT = (
    "Analyze the git diff provided via stdin. Generate a professional Conventional Commit message adapted to the complexity of the changes.\n"
    "Structure:\n"
    "type(scope): concise summary of the change\n\n"
    "[Body]\n"
    "- detailed explanation of what changed in the code\n"
    "- justification for why the change was made (if evident)\n\n"
    "Guidelines:\n"
    "1. Always start with a clear header line.\n"
    "2. If the change implies logic modification, refactoring, or new features (regardless of file count), PROVIDE A DETAILED BODY.\n"
    "3. Analyze the actual code changes (diff hunks) to describe 'what' and 'why', not just 'where'.\n"
    "4. CRITICAL: Do NOT use markdown code blocks (```). Output raw text only.\n"
    "5. STRICT STYLE RULES: Use IMPERATIVE mood (e.g., 'add' NOT 'added', 'fix' NOT 'fixed').\n"
    "6. FORBIDDEN WORDS: Do NOT use 'I', 'we', 'me', 'my', 'this commit'. Start directly with the verb.\n"
    "7. NO PREAMBLE: Start the response DIRECTLY with the commit type."
)

def extract_issue_id() -> str:
    """
    Extracts Jira-like issue ID (PROJ-123) from the current git branch name.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, encoding='utf-8'
        )
        branch_name = result.stdout.strip()
        # Match standard uppercase ticket ID: START-123 or PROJ-123
        match = re.search(r'([A-Z]+-\d+)', branch_name)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def get_staged_diff() -> str:
    try:
        subprocess.check_call(["git", "diff", "--staged", "--quiet"])
        typer.secho("No staged changes found.", fg=typer.colors.YELLOW)
        sys.exit(0)
    except subprocess.CalledProcessError:
        pass

    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.stdout

def clean_response(raw_output: str) -> str:
    """
    Removes any conversational filler or 'thinking' text before the actual commit message.
    It looks for the first line that matches the Conventional Commits pattern.
    """
    match = re.search(CONVENTIONAL_REGEX, raw_output, re.MULTILINE)
    if match:
        # Return everything starting from the match
        return raw_output[match.start():].strip()
    return raw_output.strip()

def call_external_ai(diff_content: str) -> str:
    """
    Attempts to use globally installed AI CLIs (gemini-chat, claude, etc.)
    in non-interactive mode.
    """
    # List of possible commands and their non-interactive flags
    # We prioritize gemini-chat as mentioned by the mentor
    commands = [
        {"cmd": "gemini-chat", "args": ["--system", SYSTEM_PROMPT]},
        {"cmd": "gemini", "args": [SYSTEM_PROMPT]}, # positional arg for gemini-cli
        {"cmd": "aicommits", "args": ["--generate"]}, # another popular tool
    ]

    for tool in commands:
        executable = shutil.which(tool["cmd"])
        if executable:
            try:
                # Use Pipe: echo "diff" | tool
                full_cmd = [executable] + tool["args"]
                process = subprocess.Popen(
                    full_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                stdout, stderr = process.communicate(input=diff_content)
                
                if process.returncode == 0 and stdout.strip():
                    return clean_response(stdout)
            except Exception:
                continue
    
    return ""

def call_local_fallback(diff_content: str) -> str:
    """Fallback to local heuristic engine if no AI CLI is found."""
    local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
    if os.path.exists(local_bridge):
        process = subprocess.Popen(
            [sys.executable, local_bridge],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding='utf-8'  # <--- Fix: Force UTF-8 encoding
        )
        stdout, _ = process.communicate(input=diff_content)
        return stdout.strip()
    return "chore: update files"

@app.command()
def commit():
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    typer.echo("Reading staged changes...")
    diff = get_staged_diff()
    
    typer.echo("Processing via external AI CLI...")
    message = call_external_ai(diff)
    
    if not message:
        typer.echo("AI CLI not found or failed. Using local engine...")
        message = call_local_fallback(diff)
    
    # Smart Context: Attach Issue ID if available in branch name
    issue_id = extract_issue_id()
    if issue_id:
        message += f"\n\nRefs: {issue_id}"
    
    while True:
        typer.echo("-" * 50)
        typer.secho(f"Suggested: {message}", fg=typer.colors.GREEN, bold=True)
        typer.echo("-" * 50)
        
        choice = typer.prompt("Action? [y]es, [n]o, [e]dit", default="y").lower()
        
        if choice in ['y', 'yes']:
            subprocess.run(["git", "commit", "-m", message], check=True)
            typer.secho("✅ Committed!", fg=typer.colors.GREEN)
            
            if typer.confirm("Push to remote?"):
                subprocess.run(["git", "push"])
            break
            
        elif choice in ['e', 'edit']:
            typer.echo(f"Current: {message}")
            new_message = typer.prompt("New message (leave empty to cancel edit)", default="", show_default=False)
            if new_message.strip():
                message = new_message.strip()
            else:
                typer.echo("Edit cancelled, keeping original message.")
            # Loop continues to show updated message
            
        elif choice in ['n', 'no']:
            typer.secho("Aborted.", fg=typer.colors.RED)
            sys.exit(0)
            
        else:
            typer.echo("Invalid choice.")

if __name__ == "__main__":
    app()