import subprocess
import shutil
import sys
import typer
import os
import re

app = typer.Typer()

# Wzorzec Conventional Commits
CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./\+]+\))?: .+$"

def check_dependencies():
    """Verifies that git is installed."""
    if not shutil.which("git"):
        typer.secho("Error: 'git' is not installed or not in PATH.", fg=typer.colors.RED)
        sys.exit(1)
    
    # Sprawdzamy czy mamy nasz lokalny silnik
    local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
    if not os.path.exists(local_bridge):
        typer.secho("Error: 'local_bridge.py' logic engine not found.", fg=typer.colors.RED)
        sys.exit(1)

def get_staged_diff() -> str:
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
        # Pobieramy diff
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        typer.secho(f"Git error: {e.stderr}", fg=typer.colors.RED)
        sys.exit(1)

def generate_commit_message(diff_content: str) -> str:
    """
    Pipes diff to LOCAL python script.
    No API, No Tokens.
    """
    try:
        local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
        cmd = [sys.executable, local_bridge]

        # Uruchamiamy proces (Unix Pipe style)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,  # Tu wpychamy diff
            stdout=subprocess.PIPE, # Stąd czytamy odpowiedź
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Komunikacja: wyślij diff, odbierz message
        stdout, stderr = process.communicate(input=diff_content)
        
        if process.returncode != 0:
            typer.secho(f"Engine Error: {stderr}", fg=typer.colors.RED)
            sys.exit(1)
            
        return stdout.strip()
    except Exception as e:
        typer.secho(f"Pipe Error: {str(e)}", fg=typer.colors.RED)
        sys.exit(1)

def validate_conventional(message: str) -> bool:
    return bool(re.match(CONVENTIONAL_REGEX, message))

@app.command()
def commit():
    check_dependencies()
    
    typer.echo("Reading git changes...")
    diff = get_staged_diff()
    
    # Informacja dla użytkownika
    typer.echo("Analyzing changes (Offline Mode)...")
    message = generate_commit_message(diff)
    
    typer.echo("--------------------------------------------------")
    
    is_valid = validate_conventional(message)
    if is_valid:
        typer.secho(f"Suggested Commit: {message}", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho(f"⚠️  INVALID FORMAT: {message}", fg=typer.colors.RED, bold=True)
    
    typer.echo("--------------------------------------------------")
    
    if typer.confirm("Do you want to commit with this message?"):
        subprocess.run(["git", "commit", "-m", message], check=True)
        typer.secho("✅ Success!", fg=typer.colors.GREEN)

        if typer.confirm("Do you want to push changes to remote?"):
            try:
                subprocess.run(["git", "push"], check=True)
                typer.secho("✅ Pushed successfully!", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho("❌ Push failed.", fg=typer.colors.RED)
    else:
        typer.secho("Aborted.", fg=typer.colors.YELLOW)

if __name__ == "__main__":
    app()