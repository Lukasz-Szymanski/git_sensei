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
    "Analyze the git diff below. Generate a SINGLE Conventional Commit message. "
    "Format: type(scope): description. No markdown. No explanations."
)

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

def call_external_ai(diff_content: str) -> str:
    """
    Attempts to use globally installed AI CLIs (gemini-chat, claude, etc.)
    in non-interactive mode.
    """
    # List of possible commands and their non-interactive flags
    # We prioritize gemini-chat as mentioned by the mentor
    commands = [
        {"cmd": "gemini-chat", "args": ["--system", SYSTEM_PROMPT]},
        {"cmd": "gemini", "args": ["--prompt", SYSTEM_PROMPT]}, # alternative name
        {"cmd": "aicommits", "args": ["--generate"]}, # another popular tool
    ]

    for tool in commands:
        if shutil.which(tool["cmd"]):
            try:
                # Use Pipe: echo "diff" | tool
                full_cmd = [tool["cmd"]] + tool["args"]
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
                    return stdout.strip()
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
    
    typer.echo("-" * 50)
    typer.secho(f"Suggested: {message}", fg=typer.colors.GREEN, bold=True)
    typer.echo("-" * 50)
    
    if typer.confirm("Use this message?"):
        subprocess.run(["git", "commit", "-m", message], check=True)
        typer.secho("✅ Committed!", fg=typer.colors.GREEN)
        
        if typer.confirm("Push to remote?"):
            subprocess.run(["git", "push"])

if __name__ == "__main__":
    app()