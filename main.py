import subprocess
import shutil
import sys
import typer
import os
import re

app = typer.Typer()

# Definicja wzorca Conventional Commits
# Format: typ(zakres): opis
# Typy: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./]+\))?: .+$"

SYSTEM_PROMPT = (
    "You are a Senior DevOps Engineer. Analyze the provided code diff. "
    "Generate a SINGLE commit message strictly following the Conventional Commits v1.0.0 specification. "
    "Format: <type>(<scope>): <description> "
    "Allowed types: feat, fix, docs, style, refactor, test, chore. "
    "Output ONLY the raw message string. No markdown, no explanations."
)

def check_dependencies():
    """Verifies that git and gemini-chat are installed."""
    if not shutil.which("git"):
        typer.secho("Error: 'git' is not installed or not in PATH.", fg=typer.colors.RED)
        sys.exit(1)
    
    # Check for global command OR local mock
    if not shutil.which("gemini-chat") and not os.path.exists("gemini-chat.bat"):
        typer.secho("Error: 'gemini-chat' is not installed or not in PATH.", fg=typer.colors.RED)
        sys.exit(1)

def get_staged_diff() -> str:
    """Captures staged changes using git diff."""
    try:
        subprocess.check_call(["git", "diff", "--staged", "--quiet"])
        typer.secho("No staged changes found. Use 'git add' first.", fg=typer.colors.YELLOW)
        sys.exit(0)
    except subprocess.CalledProcessError:
        pass
    except FileNotFoundError:
        typer.secho("Error: Git repository not found.", fg=typer.colors.RED)
        sys.exit(1)

    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        typer.secho(f"Git error: {e.stderr}", fg=typer.colors.RED)
        sys.exit(1)

def generate_commit_message(diff_content: str) -> str:
    """Pipes diff to gemini-chat-cli to get a commit message."""
    try:
        if os.path.exists("gemini-chat.bat"):
            executable = os.path.abspath("gemini-chat.bat")
            cmd = [executable]
        else:
            cmd = ["gemini-chat"]

        cmd.extend(["--model", "gemini-3-pro", "--system", SYSTEM_PROMPT])

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=diff_content)
        
        if process.returncode != 0:
            typer.secho(f"Gemini error: {stderr}", fg=typer.colors.RED)
            sys.exit(1)
            
        return stdout.strip()
    except Exception as e:
        typer.secho(f"Error communicating with AI: {str(e)}", fg=typer.colors.RED)
        sys.exit(1)

def validate_conventional(message: str) -> bool:
    """Checks if the message matches the Conventional Commits regex."""
    return bool(re.match(CONVENTIONAL_REGEX, message))

@app.command()
def commit():
    """
    Analyzes git changes and suggests a conventional commit message.
    """
    check_dependencies()
    
    typer.echo("Reading git changes...")
    diff = get_staged_diff()
    
    typer.echo("Asking AI (Gemini 3 Pro) for a suggestion...")
    message = generate_commit_message(diff)
    
    typer.echo("--------------------------------------------------")
    
    # --- NOWA WALIDACJA ---
    is_valid = validate_conventional(message)
    if is_valid:
        typer.secho(f"Suggested Commit: {message}", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho(f"⚠️  INVALID FORMAT: {message}", fg=typer.colors.RED, bold=True)
        typer.secho("The AI suggestion does not follow Conventional Commits standard.", fg=typer.colors.YELLOW)
    
    typer.echo("--------------------------------------------------")
    
    if typer.confirm("Do you want to commit with this message?"):
        if not is_valid:
             typer.secho("Committing with invalid format as requested...", fg=typer.colors.YELLOW)
        
        try:
            subprocess.run(["git", "commit", "-m", message], check=True)
            typer.secho("✅ Success! Commit added.", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
             typer.secho("Failed to commit.", fg=typer.colors.RED)
    else:
        typer.secho("Aborted.", fg=typer.colors.YELLOW)

if __name__ == "__main__":
    app()