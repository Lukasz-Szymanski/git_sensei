"""Git-Sensei: AI-powered commit message generator."""
import shutil
import sys
import os
import re
import typer
from typing import Optional

from config import ConfigManager
from providers import AIProvider
from secrets import scan_diff, format_warning
from git_utils import get_staged_diff, get_current_branch, extract_issue_id, create_commit

app = typer.Typer(
    help="Git-Sensei: AI-powered commit message generator. Quick start: git add . && sensei commit",
    add_completion=False,
    rich_markup_mode=None,
)
config_mgr = ConfigManager()

CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./+]+\))?: .+$"

DEFAULT_PROMPT = """OUTPUT ONLY THE COMMIT MESSAGE. NO EXPLANATIONS. NO MARKDOWN. NO COMMENTARY.

Format:
type(scope): short summary

- bullet point describing change

Rules:
- Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
- Use imperative mood: "add" not "added"
- First line max 72 characters
- NO preamble, NO markdown, NO "I/we/this commit"
- Start DIRECTLY with the type"""


def clean_response(raw_output: str) -> str:
    """Extract commit message from AI response."""
    match = re.search(CONVENTIONAL_REGEX, raw_output, re.MULTILINE)
    if match:
        return raw_output[match.start():].strip()
    return raw_output.strip()


def call_local_fallback(diff: str) -> str:
    """Fallback to local heuristic engine."""
    local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
    if os.path.exists(local_bridge):
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, local_bridge],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding='utf-8'
        )
        stdout, _ = proc.communicate(input=diff)
        return stdout.strip()
    return "chore: update files"


@app.command()
def commit(
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without committing.")
):
    """Generate a commit message using AI."""
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    # Select provider
    provider_name = provider or config_mgr.get_default_provider()
    provider_cfg = config_mgr.get_provider_config(provider_name)

    if not provider_cfg:
        typer.secho(f"Provider '{provider_name}' not found.", fg=typer.colors.RED)
        typer.echo("Use 'sensei ls' to see available providers.")
        sys.exit(1)

    typer.echo(f"Using: {provider_name}")

    # Get diff
    diff = get_staged_diff()
    if not diff:
        typer.secho("No staged changes.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # Secrets check
    secrets = scan_diff(diff)
    if secrets:
        typer.secho(format_warning(secrets), fg=typer.colors.YELLOW)
        if not typer.confirm("Continue anyway?", default=False):
            sys.exit(1)

    # Generate message
    typer.echo("Thinking...")
    prompt = provider_cfg.get("prompt", DEFAULT_PROMPT)
    ai = AIProvider(provider_name, provider_cfg)
    raw = ai.execute(diff, prompt)

    message = clean_response(raw) if raw else call_local_fallback(diff)

    # Add issue reference
    branch = get_current_branch()
    issue_id = extract_issue_id(branch)
    if issue_id:
        message += f"\n\nRefs: {issue_id}"

    # Review loop
    while True:
        typer.echo("-" * 50)
        typer.secho(message, fg=typer.colors.GREEN)
        typer.echo("-" * 50)

        if dry_run:
            break

        choice = typer.prompt("[y]es, [n]o, [e]dit, [r]etry", default="y").lower()

        if choice in ('y', 'yes'):
            if create_commit(message):
                typer.secho("Committed!", fg=typer.colors.GREEN)
            break
        elif choice in ('e', 'edit'):
            message = typer.prompt("Message", default=message).strip()
        elif choice in ('r', 'retry'):
            raw = ai.execute(diff, prompt)
            if raw:
                message = clean_response(raw)
        elif choice in ('n', 'no'):
            typer.secho("Aborted.", fg=typer.colors.RED)
            break


@app.command(name="ls")
def list_providers():
    """List available AI providers."""
    default = config_mgr.get_default_provider()
    for name, desc in config_mgr.list_providers().items():
        prefix = "*" if name == default else " "
        typer.echo(f"{prefix} {name}: {desc}")


@app.command()
def use(provider: str = typer.Argument(..., help="Provider name.")):
    """Set the default AI provider."""
    if provider not in config_mgr.list_providers():
        typer.secho(f"Provider '{provider}' not found.", fg=typer.colors.RED)
        sys.exit(1)

    if config_mgr.set_default_provider(provider):
        typer.secho(f"Default set to '{provider}'.", fg=typer.colors.GREEN)
    else:
        typer.secho("Failed to save.", fg=typer.colors.RED)
        sys.exit(1)


@app.command()
def check(provider: str = typer.Argument(None, help="Provider to check.")):
    """Check if an AI provider is working."""
    target = provider or config_mgr.get_default_provider()
    cfg = config_mgr.get_provider_config(target)

    if not cfg:
        typer.secho(f"Provider '{target}' not found.", fg=typer.colors.RED)
        sys.exit(1)

    typer.echo(f"Checking: {target}")
    ai = AIProvider(target, cfg)

    if ai.check_health():
        typer.secho("OK - executable found.", fg=typer.colors.GREEN)
    else:
        typer.secho("NOT FOUND - check PATH.", fg=typer.colors.RED)


@app.command()
def init():
    """Interactive setup wizard."""
    typer.echo("Welcome to Git-Sensei!\n")

    providers = {
        "1": ("gemini", "Google Gemini", "npm i -g @google/gemini-cli"),
        "2": ("claude", "Claude Code", "npm i -g @anthropic-ai/claude-code"),
        "3": ("openai", "OpenAI GPT-4", "pip install chatgpt-cli"),
        "4": ("ollama", "Ollama (local)", "https://ollama.ai"),
    }

    for key, (_, name, install) in providers.items():
        typer.echo(f"  {key}. {name} ({install})")

    choice = typer.prompt("\nSelect provider", default="1")
    if choice not in providers:
        typer.echo("Invalid choice.")
        sys.exit(1)

    selected, name, _ = providers[choice]
    typer.echo(f"\nSelected: {name}")

    if config_mgr.set_default_provider(selected):
        typer.secho(f"Default set to '{selected}'.", fg=typer.colors.GREEN)
        typer.echo("\nReady! Run: git add . && sensei commit")
    else:
        typer.secho("Setup failed.", fg=typer.colors.RED)


if __name__ == "__main__":
    app(prog_name="sensei")
