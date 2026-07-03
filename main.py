"""Git-Sensei: AI-powered commit message generator."""
import shutil
import sys
import os
import re
import subprocess
import tempfile
import typer
from typing import Optional

from config import ConfigManager
from providers import AIProvider
from secrets_shield import scan_diff, format_warning
from git_utils import get_staged_diff, get_current_branch, extract_issue_id, create_commit, get_git_context, get_amend_diff, amend_commit, get_last_commit_message, is_commit_pushed, get_recent_commits
app = typer.Typer(
    help="Git-Sensei: AI-powered commit message generator. Quick start: git add . && sensei commit",
    add_completion=False,
    rich_markup_mode=None,
)
config_mgr = ConfigManager()

CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./+]+\))?: .+$"

DEFAULT_PROMPT = """You are a professional git commit message generator.

TASK: Analyze the git diff and generate a complete, professional commit message.

OUTPUT FORMAT (output ONLY the commit message, nothing else):

type(scope): concise summary (max 72 chars)

Brief paragraph explaining WHAT changed and WHY (2-3 sentences).

- Bullet point for specific change 1
- Bullet point for specific change 2
- Bullet point for specific change 3

{issue_footer}

RULES:
- Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore
- Use imperative mood: "add", "fix", "update" (not "added", "fixed")
- First line max 72 characters
- Be specific about what changed and why
- Group related changes in bullet points
- NO markdown formatting, NO preamble like "Here's the commit message:"
- Start DIRECTLY with the type (feat/fix/etc)
- NO signatures like "Generated with..." or "Co-Authored-By"

{context}"""


def build_prompt_with_context(base_prompt: str, git_context: dict, prompt_cfg: dict = None, recent_commits: list = None) -> str:
    """Build final prompt with git context injected, applying prompt customization and few-shot examples."""
    # Check if config is default or missing
    is_default = False
    if not prompt_cfg:
        is_default = True
    else:
        is_default = (
            prompt_cfg.get("language") == "en" and
            prompt_cfg.get("style") == "conventional" and
            prompt_cfg.get("max_length") == 72 and
            prompt_cfg.get("template") == "conventional" and
            prompt_cfg.get("few_shot") == 3 and
            prompt_cfg.get("custom", {}).get("header", "") == "" and
            prompt_cfg.get("custom", {}).get("footer", "") == ""
        )

    context_lines = []
    if git_context.get('context_summary'):
        context_lines.append(f"CONTEXT: {git_context['context_summary']}")
    if git_context.get('branch_type'):
        context_lines.append(f"SUGGESTED TYPE: {git_context['branch_type']}")
    context_str = '\n'.join(context_lines) if context_lines else ''

    issue_id = git_context.get('issue_id')
    issue_footer = f"Closes {issue_id}" if issue_id else ""

    if is_default and base_prompt:
        return base_prompt.replace('{context}', context_str).replace('{issue_footer}', issue_footer)

    # Custom template prompt compilation
    if prompt_cfg and prompt_cfg.get("template") == "custom":
        header = prompt_cfg.get("custom", {}).get("header", "")
        footer = prompt_cfg.get("custom", {}).get("footer", "")
        context_summary = git_context.get("context_summary", "")
        
        examples_str = ""
        if recent_commits:
            limit = prompt_cfg.get("few_shot", 3)
            history = recent_commits[:limit]
            if history:
                examples_str = "Few-shot examples:\n" + "\n".join(f"- {msg}" for msg in history)
        
        parts = []
        if header:
            parts.append(header)
        if context_summary:
            parts.append(f"Context: {context_summary}")
        if examples_str:
            parts.append(examples_str)
        if footer:
            parts.append(footer)
            
        return "\n\n".join(parts)

    # Otherwise: Append rules and recent commits
    prompt = base_prompt.replace('{context}', context_str).replace('{issue_footer}', issue_footer)
    
    rules = []
    if prompt_cfg:
        if prompt_cfg.get("language"):
            rules.append(f"Language: {prompt_cfg['language']}")
        if prompt_cfg.get("style"):
            rules.append(f"Style: {prompt_cfg['style']}")
        if prompt_cfg.get("max_length"):
            rules.append(f"Max length: {prompt_cfg['max_length']} characters")
            
    if rules:
        prompt += "\n\nADDITIONAL RULES:\n" + "\n".join(f"- {rule}" for rule in rules)
        
    if recent_commits and prompt_cfg:
        limit = prompt_cfg.get("few_shot", 3)
        history = recent_commits[:limit]
        if history:
            prompt += "\n\nRECENT COMMITS:\n" + "\n".join(f"=== COMMIT ===\n{msg}\n==============" for msg in history)
            
    return prompt


def strip_signatures(message: str) -> str:
    """Remove AI-generated signatures and footers from commit message."""
    patterns = [
        r'\n*🤖.*Generated with.*$',
        r'\n*Generated with \[?Claude.*$',
        r'\n*Co-Authored-By:.*$',
        r'\n*---\n*.*Generated.*$',
        r'\n*\*Generated by.*$',
    ]
    result = message
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return result.strip()


def clean_response(raw_output: str) -> str:
    """Extract commit message from AI response and remove signatures."""
    match = re.search(CONVENTIONAL_REGEX, raw_output, re.MULTILINE)
    if match:
        message = raw_output[match.start():].strip()
    else:
        message = raw_output.strip()
    return strip_signatures(message)


GITMOJI_MAP = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "style": "🎨",
    "refactor": "♻️",
    "perf": "⚡",
    "test": "✅",
    "build": "🏗️",
    "ci": "💚",
    "chore": "🔧",
    "revert": "⏪"
}

def apply_gitmoji(message: str) -> str:
    """Insert Gitmoji prefix to conventional commit message."""
    match = re.match(r"^([a-z0-9_\-]+)(\([a-z0-9_\-\./+]+\))?:", message, re.IGNORECASE)
    if match:
        commit_type = match.group(1).lower()
        emoji = GITMOJI_MAP.get(commit_type)
        if emoji:
            return f"{emoji} {message}"
    return message


def call_local_fallback(diff: str) -> str:
    """Fallback to local heuristic engine."""
    local_bridge = os.path.join(os.path.dirname(__file__), "local_bridge.py")
    if os.path.exists(local_bridge):
        proc = subprocess.Popen(
            [sys.executable, local_bridge],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding='utf-8'
        )
        stdout, _ = proc.communicate(input=diff)
        return stdout.strip()
    return "chore: update files"


def get_editor() -> Optional[str]:
    """Get editor command using fallback chain.

    Priority: $VISUAL -> $EDITOR -> git config core.editor -> platform default
    """
    # Check environment variables
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
    if editor:
        return editor

    # Check git config
    try:
        result = subprocess.run(
            ['git', 'config', 'core.editor'],
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Platform defaults
    if sys.platform == 'win32':
        return 'notepad'
    else:
        return 'nano'


def edit_in_editor(message: str) -> Optional[str]:
    """Open message in external editor for editing.

    Returns edited message or None if editing failed/was cancelled.
    """
    editor = get_editor()
    if not editor:
        return None

    # Create temporary file with commit message
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        prefix='sensei_commit_',
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(message)
        f.write('\n\n# Edit your commit message above.')
        f.write('\n# Lines starting with # will be ignored.')
        temp_path = f.name

    try:
        # Build editor command
        if sys.platform == 'win32':
            # Windows: use shell=True for complex commands
            cmd = f'{editor} "{temp_path}"'
            subprocess.run(cmd, shell=True, check=True)
        else:
            # POSIX: split command properly
            import shlex
            cmd_parts = shlex.split(editor)
            cmd_parts.append(temp_path)
            subprocess.run(cmd_parts, check=True)

        # Read edited content
        with open(temp_path, 'r', encoding='utf-8') as f:
            edited = f.read()

        # Remove comment lines and strip
        lines = [line for line in edited.splitlines() if not line.startswith('#')]
        result = '\n'.join(lines).strip()

        return result if result else None

    except subprocess.CalledProcessError:
        typer.secho("Editor closed without saving.", fg=typer.colors.YELLOW)
        return None
    except Exception as e:
        typer.secho(f"Editor error: {e}", fg=typer.colors.RED)
        return None
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass


@app.command()
def commit(
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without committing."),
    emoji: Optional[bool] = typer.Option(None, "--emoji/--no-emoji", help="Enable/disable Gitmoji support."),
    raw: bool = typer.Option(False, "--raw", help="Output raw commit message to stdout and exit.")
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

    if not raw:
        typer.echo(f"Using: {provider_name}")

    # Get diff
    diff = get_staged_diff()
    if not diff:
        if not raw:
            typer.secho("No staged changes.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # Secrets check
    secrets_cfg = config_mgr.config.get("secrets", {})
    secrets_action = secrets_cfg.get("action", "warn").lower()

    if secrets_action != "ignore":
        secrets = scan_diff(diff, custom_patterns=secrets_cfg.get("custom_patterns"))
        if secrets:
            if not raw:
                typer.secho(format_warning(secrets), fg=typer.colors.YELLOW)
                if secrets_action == "block":
                    typer.secho("Commit blocked due to detected secrets (action=block).", fg=typer.colors.RED)
                    sys.exit(1)
                elif not typer.confirm("Continue anyway?", default=False):
                    sys.exit(1)
            else:
                if secrets_action == "block":
                    sys.exit(1)

    # Gather git context
    git_context = get_git_context()

    # Show context info
    if not raw and git_context.get('context_summary'):
        typer.secho(f"Context: {git_context['context_summary']}", fg=typer.colors.CYAN)

    # Generate message
    if not raw:
        typer.echo("Thinking...")
    # Priority: provider-specific prompt > universal prompt > default
    base_prompt = provider_cfg.get("prompt") or config_mgr.get_universal_prompt() or DEFAULT_PROMPT
    prompt_cfg = config_mgr.get_prompt_config()
    limit = prompt_cfg.get("few_shot", 3)
    recent_commits = get_recent_commits(limit=limit, start_ref="HEAD")
    prompt = build_prompt_with_context(base_prompt, git_context, prompt_cfg, recent_commits)
    ai = AIProvider(provider_name, provider_cfg)
    raw_response = ai.execute(diff, prompt)

    message = clean_response(raw_response) if raw_response else call_local_fallback(diff)

    # Apply Gitmoji if enabled
    use_emoji = emoji if emoji is not None else config_mgr.config.get("core", {}).get("emoji", False)
    if use_emoji:
        message = apply_gitmoji(message)

    if raw:
        print(message)
        sys.exit(0)

    # Review loop
    while True:
        typer.echo("-" * 50)
        typer.secho(message, fg=typer.colors.GREEN)
        typer.echo("-" * 50)

        if dry_run:
            break

        choice = typer.prompt("[y]es, [n]o, [e]edit, [r]etry", default="y").lower()

        if choice in ('y', 'yes'):
            if create_commit(message):
                typer.secho("Committed!", fg=typer.colors.GREEN)
            break
        elif choice in ('e', 'edit'):
            edited = edit_in_editor(message)
            if edited:
                message = edited
            else:
                typer.secho("Edit cancelled, keeping original message.", fg=typer.colors.YELLOW)
        elif choice in ('r', 'retry'):
            raw = ai.execute(diff, prompt)
            if raw:
                message = clean_response(raw)
                if use_emoji:
                    message = apply_gitmoji(message)
        elif choice in ('n', 'no'):
            typer.secho("Aborted.", fg=typer.colors.RED)
            break


@app.command()
def amend(
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without amending."),
    emoji: Optional[bool] = typer.Option(None, "--emoji/--no-emoji", help="Enable/disable Gitmoji support."),
    raw: bool = typer.Option(False, "--raw", help="Output raw commit message to stdout and exit.")
):
    """Rewrite last commit message with AI."""
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    provider_name = provider or config_mgr.get_default_provider()
    provider_cfg = config_mgr.get_provider_config(provider_name)

    if not provider_cfg:
        typer.secho(f"Provider '{provider_name}' not found.", fg=typer.colors.RED)
        typer.echo("Use 'sensei ls' to see available providers.")
        sys.exit(1)

    if not raw:
        typer.echo(f"Using: {provider_name}")

    diff = get_amend_diff()
    if not diff:
        if not raw:
            typer.secho("No commits to amend or no changes found.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # Secrets check
    secrets_cfg = config_mgr.config.get("secrets", {})
    secrets_action = secrets_cfg.get("action", "warn").lower()

    if secrets_action != "ignore":
        secrets = scan_diff(diff, custom_patterns=secrets_cfg.get("custom_patterns"))
        if secrets:
            if not raw:
                typer.secho(format_warning(secrets), fg=typer.colors.YELLOW)
                if secrets_action == "block":
                    typer.secho("Amend blocked due to detected secrets (action=block).", fg=typer.colors.RED)
                    sys.exit(1)
                elif not typer.confirm("Continue anyway?", default=False):
                    sys.exit(1)
            else:
                if secrets_action == "block":
                    sys.exit(1)

    git_context = get_git_context()

    current_msg = get_last_commit_message() or ""
    
    if not raw and is_commit_pushed():
        typer.secho("⚠️  WARNING: The last commit has already been pushed to a remote.", fg=typer.colors.YELLOW)
        typer.secho("Amending will rewrite history and require a force push.", fg=typer.colors.YELLOW)
        if not typer.confirm("Continue anyway?", default=True):
            sys.exit(0)

    if not raw and git_context.get('context_summary'):
        typer.secho(f"Context: {git_context['context_summary']}", fg=typer.colors.CYAN)

    if not raw:
        typer.echo("Thinking...")
    
    base_prompt = provider_cfg.get("prompt") or config_mgr.get_universal_prompt() or DEFAULT_PROMPT
    prompt_cfg = config_mgr.get_prompt_config()
    limit = prompt_cfg.get("few_shot", 3)
    recent_commits = get_recent_commits(limit=limit, start_ref="HEAD~1")
    prompt = build_prompt_with_context(base_prompt, git_context, prompt_cfg, recent_commits)
    ai = AIProvider(provider_name, provider_cfg)
    raw_response = ai.execute(diff, prompt)

    message = clean_response(raw_response) if raw_response else call_local_fallback(diff)

    use_emoji = emoji if emoji is not None else config_mgr.config.get("core", {}).get("emoji", False)
    if use_emoji:
        message = apply_gitmoji(message)

    if raw:
        print(message)
        sys.exit(0)

    while True:
        typer.echo("-" * 50)
        if current_msg:
            typer.echo("Current:   ", nl=False)
            typer.secho(current_msg, fg=typer.colors.RED)
        typer.echo("Suggested: ", nl=False)
        typer.secho(message, fg=typer.colors.GREEN)
        typer.echo("-" * 50)

        if dry_run:
            break

        choice = typer.prompt("[y]es, [n]o, [e]edit, [r]etry", default="y").lower()

        if choice in ('y', 'yes'):
            if amend_commit(message):
                typer.secho("Amended!", fg=typer.colors.GREEN)
            break
        elif choice in ('e', 'edit'):
            edited = edit_in_editor(message)
            if edited:
                message = edited
            else:
                typer.secho("Edit cancelled, keeping original message.", fg=typer.colors.YELLOW)
        elif choice in ('r', 'retry'):
            raw_resp = ai.execute(diff, prompt)
            if raw_resp:
                message = clean_response(raw_resp)
                if use_emoji:
                    message = apply_gitmoji(message)
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

    # Check for existing config
    config_path = os.path.expanduser("~/.sensei.toml")
    if os.path.exists(config_path):
        typer.secho("Existing configuration found.", fg=typer.colors.YELLOW)
        if not typer.confirm("Overwrite?", default=False):
            typer.echo("Keeping existing config.")
            return

    providers = {
        "1": ("gemini", "Google Gemini", "npm i -g @google/gemini-cli"),
        "2": ("claude", "Claude Code", "npm i -g @anthropic-ai/claude-code"),
        "3": ("openai", "OpenAI GPT-4", "pip install chatgpt-cli"),
        "4": ("ollama", "Ollama (local)", "https://ollama.ai"),
    }

    typer.echo("Select your AI provider:\n")
    for key, (_, name, install) in providers.items():
        typer.echo(f"  {key}. {name} ({install})")

    choice = typer.prompt("\nSelect provider", default="1")
    if choice not in providers:
        typer.secho("Invalid choice.", fg=typer.colors.RED)
        sys.exit(1)

    selected, name, install_cmd = providers[choice]
    typer.echo(f"\nSelected: {name}")

    # Get provider config for connection test
    provider_cfg = config_mgr.get_provider_config(selected)
    if not provider_cfg:
        typer.secho(f"Provider '{selected}' not configured.", fg=typer.colors.RED)
        sys.exit(1)

    # Test connection
    typer.echo("Testing connection... ", nl=False)
    ai = AIProvider(selected, provider_cfg)
    success, msg = ai.test_connection()

    if success:
        typer.secho("OK", fg=typer.colors.GREEN)
    else:
        typer.secho("FAILED", fg=typer.colors.RED)
        typer.echo(f"  {msg}")
        typer.echo(f"\nInstall: {install_cmd}")
        if not typer.confirm("\nContinue anyway?", default=False):
            sys.exit(1)

    # Save config
    if config_mgr.set_default_provider(selected):
        typer.secho(f"\nConfig saved to {config_path}", fg=typer.colors.GREEN)
        typer.echo(f"Default provider: {selected}")
        typer.echo("\nReady! Run: git add . && sensei commit")
    else:
        typer.secho("Setup failed.", fg=typer.colors.RED)
        sys.exit(1)


@app.command(name="install-hook")
def install_hook():
    """Install git prepare-commit-msg hook in current repository."""
    git_dir = ".git"
    if not os.path.exists(git_dir):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True, text=True, check=True
            )
            git_dir = result.stdout.strip()
        except Exception:
            typer.secho("Error: Not a git repository!", fg=typer.colors.RED)
            sys.exit(1)

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    hook_content = """#!/bin/sh
# Git-Sensei Hook
# Automatically generated by 'sensei install-hook'

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

if [ -z "$COMMIT_SOURCE" ]; then
  if command -v sensei >/dev/null 2>&1; then
    sensei commit --raw > "$COMMIT_MSG_FILE"
  else
    python "{script_path}" commit --raw > "$COMMIT_MSG_FILE"
  fi
fi
""".format(script_path=os.path.abspath(__file__))

    try:
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)
        import stat
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        typer.secho(f"Hook installed successfully at {hook_path}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Failed to install hook: {e}", fg=typer.colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    app(prog_name="sensei")
