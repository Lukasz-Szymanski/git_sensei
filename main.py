import subprocess
import shutil
import sys
import typer
import os
import re
from typing import Optional

# Local module imports
from config import ConfigManager
from providers import AIProvider

app = typer.Typer(
    help="🥋 Git-Sensei: AI-powered commit assistant.\n\nQuick Start: Run 'sensei commit' to generate a message for staged changes.",
    add_completion=False
)
config_mgr = ConfigManager()

# Conventional Commits Regex
CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./+]+\))?: .+$"

# System prompt
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

def extract_issue_id() -> Optional[str]:
    """Extracts Jira-like issue ID (PROJ-123) from the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, encoding='utf-8'
        )
        branch_name = result.stdout.strip()
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
    match = re.search(CONVENTIONAL_REGEX, raw_output, re.MULTILINE)
    if match:
        return raw_output[match.start():].strip()
    return raw_output.strip()

def call_local_fallback(diff_content: str) -> str:
    """Fallback to local heuristic engine."""
    local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
    if os.path.exists(local_bridge):
        process = subprocess.Popen(
            [sys.executable, local_bridge],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        stdout, _ = process.communicate(input=diff_content)
        return stdout.strip()
    return "chore: update files"

@app.command()
def commit(
    provider: str = typer.Option(None, help="Override AI provider (e.g., 'claude', 'gemini'). Defaults to config."),
    dry_run: bool = typer.Option(False, help="Show the message but do not commit.")
):
    """
    Generates a commit message using the configured AI provider.
    """
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    # 1. Select Provider
    selected_provider_name = provider if provider else config_mgr.get_default_provider()
    provider_cfg = config_mgr.get_provider_config(selected_provider_name)
    
    if not provider_cfg:
        typer.secho(f"❌ Provider '{selected_provider_name}' not found in configuration.", fg=typer.colors.RED)
        typer.echo("Available providers:")
        for name, desc in config_mgr.list_providers().items():
            typer.echo(f" - {name}: {desc}")
        sys.exit(1)

    ai_engine = AIProvider(selected_provider_name, provider_cfg)
    
    typer.echo(f"🥋 Sensei using provider: {selected_provider_name}")
    typer.echo("Reading staged changes...")
    diff = get_staged_diff()

    # 2. Execute AI
    typer.echo("Thinking...")
    raw_message = ai_engine.execute(diff, SYSTEM_PROMPT)
    
    if raw_message:
        message = clean_response(raw_message)
    else:
        typer.echo("⚠️ AI Provider failed or returned empty. Using Local Fallback.")
        message = call_local_fallback(diff)

    # 3. Smart Context
    issue_id = extract_issue_id()
    if issue_id:
        message += f"\n\nRefs: {issue_id}"
    
    # 4. Review Loop
    while True:
        typer.echo("-" * 50)
        typer.secho(f"Suggested: {message}", fg=typer.colors.GREEN, bold=True)
        typer.echo("-" * 50)
        
        if dry_run:
            typer.echo("[Dry Run] Exiting.")
            break

        choice = typer.prompt("Action? [y]es, [n]o, [e]dit, [r]etry", default="y").lower()
        
        if choice in ['y', 'yes']:
            subprocess.run(["git", "commit", "-m", message], check=True)
            typer.secho("✅ Committed!", fg=typer.colors.GREEN)
            
            # Simple push check
            # if typer.confirm("Push to remote?"):
            #    subprocess.run(["git", "push"])
            break
            
        elif choice in ['e', 'edit']:
            typer.echo(f"Current: {message}")
            new_message = typer.prompt("New message", default=message)
            message = new_message.strip()
            
        elif choice in ['r', 'retry']:
            typer.echo("Retrying generation...")
            # We could add 'retry_prompt' logic here later
            raw_message = ai_engine.execute(diff, SYSTEM_PROMPT)
            if raw_message:
                message = clean_response(raw_message)
            # Loop continues with new message
            
        elif choice in ['n', 'no']:
            typer.secho("Aborted.", fg=typer.colors.RED)
            sys.exit(0)
            
        else:
            typer.echo("Invalid choice.")

@app.command(name="list-providers")
def list_providers():
    """Lists all available AI providers from configuration."""
    _list_providers_impl()

@app.command(name="ls", hidden=True)
def list_providers_alias():
    """Alias for list-providers"""
    _list_providers_impl()

def _list_providers_impl():
    typer.echo("Available Providers (.sensei.toml):")
    default = config_mgr.get_default_provider()
    for name, desc in config_mgr.list_providers().items():
        prefix = "*" if name == default else " "
        typer.echo(f"{prefix} {name:<10} : {desc}")

@app.command(name="check")
def check(provider: str = typer.Argument(None, help="Specific provider to check. If empty, checks default.")):
    """
    Diagnose provider connection. 
    Runs the provider's command to verify it's executable and found in PATH.
    Does NOT verify authentication (unless the tool returns specific error codes).
    """
    _check_impl(provider)

@app.command(name="doctor", hidden=True)
def check_alias(provider: str = typer.Argument(None)):
    """Alias for check"""
    _check_impl(provider)

def _check_impl(provider: Optional[str]):
    target = provider if provider else config_mgr.get_default_provider()
    cfg = config_mgr.get_provider_config(target)
    
    if not cfg:
        typer.secho(f"❌ Provider '{target}' not found.", fg=typer.colors.RED)
        sys.exit(1)
        
    engine = AIProvider(target, cfg)
    typer.echo(f"Checking provider: {target}...")
    
    if engine.check_health():
        typer.secho(f"✅ Executable found for '{target}'.", fg=typer.colors.GREEN)
        typer.echo(f"Command template: {cfg.get('command')}")
        typer.echo("\nTo verify authentication, try creating a commit or run the tool manually.")
    else:
        typer.secho(f"❌ Executable NOT found for '{target}'.", fg=typer.colors.RED)
        typer.echo("Please check your PATH or install the required CLI tool.")

if __name__ == "__main__":
    app(prog_name="sensei")
