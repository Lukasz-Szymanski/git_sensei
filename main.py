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
from secrets import scan_diff, format_warning

app = typer.Typer(
    help="Git-Sensei: AI-powered commit message generator. Quick start: git add . && sensei commit",
    add_completion=False,
    rich_markup_mode=None,  # Disable rich to avoid encoding issues on Windows
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
    provider: str = typer.Option(None, "--provider", "-p", help="AI provider to use (e.g., 'claude', 'gemini')."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview message without committing.")
):
    """
    Generate a commit message using AI.

    Analyzes staged changes and generates a Conventional Commit message.
    You can review, edit, or retry before committing.
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
    
    typer.echo(f"Sensei using provider: {selected_provider_name}")
    typer.echo("Reading staged changes...")
    diff = get_staged_diff()

    # 2. Secrets Shield - scan for potential secrets
    secret_matches = scan_diff(diff)
    if secret_matches:
        typer.secho(format_warning(secret_matches), fg=typer.colors.YELLOW)
        if not typer.confirm("Continue anyway? (secrets will be sent to AI provider)", default=False):
            typer.secho("Aborted. Remove secrets before committing.", fg=typer.colors.RED)
            sys.exit(1)

    # 3. Execute AI
    typer.echo("Thinking...")
    raw_message = ai_engine.execute(diff, SYSTEM_PROMPT)

    if raw_message:
        message = clean_response(raw_message)
    else:
        typer.echo("AI Provider failed or returned empty. Using Local Fallback.")
        message = call_local_fallback(diff)

    # 4. Smart Context
    issue_id = extract_issue_id()
    if issue_id:
        message += f"\n\nRefs: {issue_id}"

    # 5. Review Loop
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
    """
    List all available AI providers.

    Shows providers from .sensei.toml. Default is marked with *.
    """
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

@app.command(name="use")
def use_provider(
    provider: str = typer.Argument(..., help="Provider name (e.g., 'claude', 'gemini').")
):
    """
    Set the default AI provider.

    Saves to ~/.sensei.toml. Use 'sensei ls' to see available providers.
    """
    available = config_mgr.list_providers()

    if provider not in available:
        typer.secho(f"❌ Provider '{provider}' not found.", fg=typer.colors.RED)
        typer.echo("\nAvailable providers:")
        for name, desc in available.items():
            typer.echo(f"  - {name}: {desc}")
        sys.exit(1)

    if config_mgr.set_default_provider(provider):
        typer.secho(f"✅ Default provider set to '{provider}'.", fg=typer.colors.GREEN)
        typer.echo(f"Config saved to: {config_mgr.get_config_path()}")
    else:
        typer.secho(f"❌ Failed to save configuration.", fg=typer.colors.RED)
        sys.exit(1)

@app.command(name="init")
def init():
    """
    Interactive setup wizard for first-time configuration.

    Helps you choose an AI provider and saves config to ~/.sensei.toml.
    """
    typer.echo("Welcome to Git-Sensei!")
    typer.echo("-" * 40)

    # Available providers with install instructions
    providers_info = {
        "gemini": {
            "name": "Google Gemini CLI",
            "install": "npm install -g @google/gemini-cli",
            "command": 'gemini "{system}"'
        },
        "claude": {
            "name": "Claude Code (Anthropic)",
            "install": "npm install -g @anthropic-ai/claude-code",
            "command": 'claude --print "{system}"'
        },
        "openai": {
            "name": "OpenAI ChatGPT",
            "install": "pip install chatgpt-cli",
            "command": 'chatgpt -m gpt-4 --system "{system}"'
        },
        "ollama": {
            "name": "Ollama (Local)",
            "install": "https://ollama.ai",
            "command": 'ollama run llama3 "{system}"'
        }
    }

    # Show options
    typer.echo("\nAvailable AI providers:\n")
    provider_list = list(providers_info.keys())
    for i, key in enumerate(provider_list, 1):
        info = providers_info[key]
        typer.echo(f"  {i}. {info['name']}")
        typer.echo(f"     Install: {info['install']}")

    typer.echo("")

    # Get user choice
    while True:
        choice = typer.prompt("Select provider (1-4)", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(provider_list):
                selected = provider_list[idx]
                break
            else:
                typer.echo("Invalid choice. Enter 1-4.")
        except ValueError:
            typer.echo("Invalid choice. Enter 1-4.")

    selected_info = providers_info[selected]
    typer.echo(f"\nSelected: {selected_info['name']}")

    # Check if provider is installed
    typer.echo("Checking if CLI tool is installed...")
    test_engine = AIProvider(selected, {"command": selected_info["command"]})

    if test_engine.check_health():
        typer.secho("OK - CLI tool found!", fg=typer.colors.GREEN)
    else:
        typer.secho("WARNING - CLI tool not found in PATH.", fg=typer.colors.YELLOW)
        typer.echo(f"Install with: {selected_info['install']}")
        if not typer.confirm("Continue anyway?", default=True):
            typer.echo("Aborted.")
            sys.exit(0)

    # Save config
    config_path = config_mgr.get_config_path()

    config_content = f'''[core]
default_provider = "{selected}"

[providers.{selected}]
description = "{selected_info['name']}"
command = '{selected_info['command']}'
'''

    # Check if config exists
    if os.path.exists(config_path):
        if not typer.confirm(f"\n{config_path} exists. Overwrite?", default=False):
            # Just update default provider
            if config_mgr.set_default_provider(selected):
                typer.secho(f"\nDefault provider set to '{selected}'.", fg=typer.colors.GREEN)
            sys.exit(0)

    # Write new config
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    typer.secho(f"\nConfig saved to: {config_path}", fg=typer.colors.GREEN)
    typer.echo("\nYou're ready! Try:")
    typer.echo("  git add .")
    typer.echo("  sensei commit")

@app.command(name="check")
def check(provider: str = typer.Argument(None, help="Provider to check (defaults to current).")):
    """
    Check if an AI provider is working.

    Verifies CLI tool is installed and in PATH. Does not check authentication.
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
