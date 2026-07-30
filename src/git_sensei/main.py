"""Git-Sensei: AI-powered commit message generator."""
import shutil
import sys
import os
import re
import subprocess
import tempfile
import typer
import json
from typing import Optional

from git_sensei.config import ConfigManager
from git_sensei.constants import (
    GITMOJI_MAP, COMMIT_TYPES, CONVENTIONAL_REGEX, CONVENTIONAL_PATTERN,
    DEFAULT_PROMPT, REVIEW_CHOICES, PR_MAX_DIFF_LENGTH,
)
from git_sensei.core.stats import get_stats_file_path, parse_commit_type, record_commit_stat, load_stats, clear_stats
from git_sensei.core.editor import get_editor, edit_in_editor
from git_sensei.core.fallback import generate_fallback_message
from git_sensei.providers import AIProvider
from git_sensei.secrets_shield import scan_diff, format_warning, redact_secrets
from git_sensei.git_utils import (
    get_staged_diff, get_current_branch, extract_issue_id, create_commit,
    get_git_context, get_amend_diff, amend_commit, get_last_commit_message,
    is_commit_pushed, get_recent_commits, get_staged_diff_filtered,
    split_staged_diff, get_staged_files,
)

app = typer.Typer(
    help="Git-Sensei: AI-powered commit message generator. Quick start: git add . && sensei commit",
    add_completion=False,
    rich_markup_mode=None,
)
config_mgr = ConfigManager()

def display_truncation_metadata(meta: dict, raw: bool):
    """Helper to display warnings for skipped or truncated files."""
    if raw:
        return
    skipped = meta.get("skipped", {})
    if skipped:
        typer.secho(f"Note: Skipped {len(skipped)} files (lockfiles, binaries, minified, or truncated)", fg=typer.colors.YELLOW)
        for filepath, reason in skipped.items():
            typer.secho(f"  - {filepath} ({reason})", fg=typer.colors.YELLOW)
    if meta.get("truncated"):
        typer.secho(f"Warning: Diff was truncated using strategy '{meta.get('strategy')}' as it exceeded token budget.", fg=typer.colors.RED)


def generate_and_review_commit_for_diff(
    diff: str,
    provider_name: str,
    provider_cfg: dict,
    raw: bool,
    dry_run: bool,
    emoji: Optional[bool]
) -> bool:
    """
    Generates a commit message for a given diff, displays the context, and runs
    the interactive review loop. Returns True if committed, False if aborted.
    """
    # Gather git context
    git_context = get_git_context(config_mgr.config)

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
    secrets_cfg = config_mgr.config.get("secrets", {})
    diff_redacted = redact_secrets(diff, custom_patterns=secrets_cfg.get("custom_patterns"))
    ai = AIProvider(provider_name, provider_cfg)
    raw_response = ai.execute(diff_redacted, prompt)

    message = clean_response(raw_response) if raw_response else call_local_fallback(diff)

    # Apply Gitmoji if enabled
    use_emoji = emoji if emoji is not None else config_mgr.config.get("core", {}).get("emoji", False)
    if use_emoji:
        message = apply_gitmoji(message)

    if raw:
        print(message)
        return True

    # Review loop
    while True:
        typer.echo("-" * 50)
        typer.secho(message, fg=typer.colors.GREEN)
        typer.echo("-" * 50)

        if dry_run:
            return True

        choice = typer.prompt(REVIEW_CHOICES, default="y").lower()

        if choice in ('y', 'yes'):
            if create_commit(message):
                typer.secho("Committed!", fg=typer.colors.GREEN)
                record_commit_stat(provider_name, "accepted", parse_commit_type(message), len(message))
                return True
            return False
        elif choice in ('e', 'edit'):
            edited = edit_in_editor(message)
            if edited:
                message = edited
            else:
                typer.secho("Edit cancelled, keeping original message.", fg=typer.colors.YELLOW)
        elif choice in ('r', 'retry'):
            raw_res = ai.execute(diff, prompt)
            if raw_res:
                message = clean_response(raw_res)
                if use_emoji:
                    message = apply_gitmoji(message)
        elif choice in ('f', 'refine'):
            refinement_text = typer.prompt("Enter refinement instructions")
            refine_prompt = (
                f"{prompt}\n\n"
                f"PREVIOUS SUGGESTION:\n{message}\n\n"
                f"USER REFINEMENT INSTRUCTION:\n{refinement_text}\n\n"
                f"Generate a new commit message that incorporates the user's refinement instructions."
            )
            typer.echo("Refining...")
            raw_res = ai.execute(diff, refine_prompt)
            if raw_res:
                message = clean_response(raw_res)
                if use_emoji:
                    message = apply_gitmoji(message)
        elif choice in ('s', 'select'):
            types = COMMIT_TYPES
            gitmojis = GITMOJI_MAP
            typer.echo("Select commit type:")
            for i, t in enumerate(types, 1):
                typer.echo(f"  {i}. {t} {gitmojis.get(t, '')}")
            type_choice = typer.prompt("Choose type (number or name)", default="1")
            
            selected_type = "feat"
            if type_choice.isdigit():
                idx = int(type_choice) - 1
                if 0 <= idx < len(types):
                    selected_type = types[idx]
            elif type_choice in types:
                selected_type = type_choice
            
            include_emoji = typer.confirm("Include Gitmoji?", default=use_emoji)
            message = update_commit_message_header(message, selected_type, include_emoji)
        elif choice in ('n', 'no'):
            typer.secho("Aborted.", fg=typer.colors.RED)
            record_commit_stat(provider_name, "rejected", parse_commit_type(message), len(message))
            return False

# CONVENTIONAL_REGEX, DEFAULT_PROMPT - now imported from constants


def update_commit_message_header(message: str, new_type: str, include_emoji: bool) -> str:
    """Updates the commit message's first line type and emoji prefix."""
    lines = message.splitlines()
    if not lines:
        return message
    first_line = lines[0]
    
    # Match conventional commit header pattern
    # Optional emoji at the start, followed by type, optional (scope), and subject
    pattern = r"^(?P<emoji>(?::\w+:|[\U00010000-\U0010ffff]\s*))?\s*(?P<type>[a-zA-Z0-9_-]+)(?P<scope>\([^)]+\))?(?P<breaking>!)?\s*:\s*(?P<subject>.*)$"
    match = re.match(pattern, first_line)
    
    gitmojis = GITMOJI_MAP
    
    emoji_prefix = (gitmojis.get(new_type, "") + " ") if (include_emoji and new_type in gitmojis) else ""
    
    if match:
        scope = match.group("scope") or ""
        breaking = match.group("breaking") or ""
        subject = match.group("subject") or ""
        # Reconstruct first line
        lines[0] = f"{emoji_prefix}{new_type}{scope}{breaking}: {subject}"
    else:
        # Fallback if first line is not conventional commit format
        lines[0] = f"{emoji_prefix}{new_type}: {first_line}"
        
    return "\n".join(lines)


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
    if git_context.get('scope'):
        context_lines.append(f"SUGGESTED SCOPE: {git_context['scope']}")
    if git_context.get('issue_context'):
        context_lines.append(f"ISSUE DETAILS (from tracker):\n{git_context['issue_context']}")
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
    return generate_fallback_message(diff)


@app.command()
def commit(
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without committing."),
    emoji: Optional[bool] = typer.Option(None, "--emoji/--no-emoji", help="Enable/disable Gitmoji support."),
    raw: bool = typer.Option(False, "--raw", help="Output raw commit message to stdout and exit."),
    split: bool = typer.Option(False, "--split", help="Split staged changes into separate atomic commits.")
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
    diff, truncation_meta = get_staged_diff_filtered(config_mgr.config)
    if not diff:
        if not raw:
            typer.secho("No staged changes.", fg=typer.colors.YELLOW)
        sys.exit(0)

    display_truncation_metadata(truncation_meta, raw)

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

    # Split flow
    if split:
        groups = split_staged_diff(diff)
        if len(groups) > 1:
            if not raw:
                typer.echo(f"Detected {len(groups)} independent changes:")
                for idx, group in enumerate(groups, 1):
                    files_str = ", ".join(group["files"])
                    typer.echo(f"  {idx}. {group['suggested_message']} (files: {files_str})")
            
            if raw or typer.confirm("Split into separate commits?", default=True):
                # Save original staged files
                original_files = get_staged_files()
                
                # Unstage all
                subprocess.run(["git", "reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                try:
                    for idx, group in enumerate(groups, 1):
                        if not raw:
                            typer.echo(f"\nStaging changes for commit {idx}/{len(groups)}...")
                        for f in group["files"]:
                            subprocess.run(["git", "add", f], check=True)
                        
                        group_diff = get_staged_diff()
                        if not group_diff:
                            if not raw:
                                typer.echo(f"No changes found for group {idx}. Skipping.")
                            continue
                        
                        success = generate_and_review_commit_for_diff(
                            diff=group_diff,
                            provider_name=provider_name,
                            provider_cfg=provider_cfg,
                            raw=raw,
                            dry_run=dry_run,
                            emoji=emoji
                        )
                        if not success:
                            if not raw:
                                typer.secho(f"Commit {idx}/{len(groups)} aborted.", fg=typer.colors.RED)
                                if not typer.confirm("Proceed with remaining groups?", default=True):
                                    break
                finally:
                    # Re-stage any remaining uncommitted files that were originally staged
                    for f in original_files:
                        try:
                            res = subprocess.run(["git", "status", "--porcelain", f], capture_output=True, text=True)
                            if res.stdout.strip():
                                subprocess.run(["git", "add", f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
                return

    # Normal commit flow
    generate_and_review_commit_for_diff(
        diff=diff,
        provider_name=provider_name,
        provider_cfg=provider_cfg,
        raw=raw,
        dry_run=dry_run,
        emoji=emoji
    )


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

    raw_diff = get_amend_diff()
    if not raw_diff:
        if not raw:
            typer.secho("No commits to amend or no changes found.", fg=typer.colors.YELLOW)
        sys.exit(0)

    diff, truncation_meta = get_staged_diff_filtered(config_mgr.config, diff_override=raw_diff)
    if not diff:
        if not raw:
            typer.secho("No commits to amend or no changes found after filtering.", fg=typer.colors.YELLOW)
        sys.exit(0)

    display_truncation_metadata(truncation_meta, raw)

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

    git_context = get_git_context(config_mgr.config)

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

        choice = typer.prompt(REVIEW_CHOICES, default="y").lower()

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
        elif choice in ('f', 'refine'):
            refinement_text = typer.prompt("Enter refinement instructions")
            refine_prompt = (
                f"{prompt}\n\n"
                f"PREVIOUS SUGGESTION:\n{message}\n\n"
                f"USER REFINEMENT INSTRUCTION:\n{refinement_text}\n\n"
                f"Generate a new commit message that incorporates the user's refinement instructions."
            )
            if not raw:
                typer.echo("Refining...")
            raw_resp = ai.execute(diff, refine_prompt)
            if raw_resp:
                message = clean_response(raw_resp)
                if use_emoji:
                    message = apply_gitmoji(message)
        elif choice in ('s', 'select'):
            types = COMMIT_TYPES
            gitmojis = GITMOJI_MAP
            typer.echo("Select commit type:")
            for i, t in enumerate(types, 1):
                typer.echo(f"  {i}. {t} {gitmojis.get(t, '')}")
            type_choice = typer.prompt("Choose type (number or name)", default="1")
            
            selected_type = "feat"
            if type_choice.isdigit():
                idx = int(type_choice) - 1
                if 0 <= idx < len(types):
                    selected_type = types[idx]
            elif type_choice in types:
                selected_type = type_choice
            
            include_emoji = typer.confirm("Include Gitmoji?", default=use_emoji)
            message = update_commit_message_header(message, selected_type, include_emoji)
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
        "1": ("antigravity", "Google Antigravity", "npm i -g @google/antigravity-cli"),
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


@app.command(name="squash")
def squash(
    base: str = typer.Option("main", "-b", "--base", help="Base branch to squash against."),
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without squashing.")
):
    """Smartly rebase and squash messy commits using AI."""
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    # 1. Get commits between base and HEAD
    try:
        log_output = subprocess.check_output(
            ["git", "log", f"{base}..HEAD", "--pretty=format:%h %s", "--name-status"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        typer.secho(f"Could not find commits between {base} and HEAD. Does {base} exist?", fg=typer.colors.RED)
        sys.exit(1)

    if not log_output:
        typer.secho(f"No commits ahead of {base}.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # Count commits
    try:
        commit_count = int(subprocess.check_output(
            ["git", "rev-list", "--count", f"{base}..HEAD"], text=True
        ).strip())
    except:
        commit_count = 0

    if commit_count < 2:
        typer.secho("Need at least 2 commits to squash.", fg=typer.colors.YELLOW)
        sys.exit(0)

    typer.echo(f"Found {commit_count} commits ahead of {base}.")
    
    # 2. Select provider
    provider_name = provider or config_mgr.get_default_provider()
    provider_cfg = config_mgr.get_provider_config(provider_name)

    if not provider_cfg:
        typer.secho(f"Provider '{provider_name}' not found.", fg=typer.colors.RED)
        sys.exit(1)

    typer.echo("Analyzing commits with AI to generate a rebase plan...")

    # 3. Generate prompt
    system_prompt = (
        "You are an expert Git user. I will give you a list of commits with their short hashes, "
        "subjects, and files changed.\n"
        "Your task is to generate a git rebase interactive script that logically groups these commits.\n"
        "Use 'pick' for the first commit of a logical group.\n"
        "Use 'fixup' for subsequent commits that belong to the same logical group (like typos, wip, or related changes).\n"
        "Do NOT change the order of the commits unless absolutely necessary.\n"
        "OUTPUT ONLY the raw rebase script without any markdown blocks or explanations."
    )

    # Reversing the log because rebase script is chronologically ordered (oldest first)
    try:
        chrono_log = subprocess.check_output(
            ["git", "log", f"{base}..HEAD", "--reverse", "--pretty=format:%h %s", "--name-status"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        chrono_log = log_output

    prompt_text = f"{system_prompt}\n\nCommits to rebase:\n{chrono_log}"

    # 4. Call AI provider
    try:
        ai = AIProvider(provider_name, provider_cfg)
        plan = ai.execute(prompt_text, system_prompt=system_prompt)
    except Exception as e:
        typer.secho(f"\nAI Error: {str(e)}", fg=typer.colors.RED)
        sys.exit(1)

    # Clean markdown if provided
    plan = re.sub(r'```[a-zA-Z]*\n', '', plan)
    plan = plan.replace('```', '').strip()

    if dry_run:
        typer.echo("\n--- Generated Rebase Plan (Dry Run) ---")
        typer.echo(plan)
        typer.echo("---------------------------------------")
        sys.exit(0)

    typer.echo("\n--- Generated Rebase Plan ---")
    typer.echo(plan)
    typer.echo("-----------------------------")

    if not typer.confirm("Apply this rebase plan?", default=True):
        typer.secho("Aborted.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # 5. Apply rebase

    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(plan)
        plan_path = f.name

    typer.echo("Executing git rebase -i...")
    
    # We create a script that just copies our plan over the rebase-todo
    sequence_editor = f"python3 -c \"import shutil, sys; shutil.copy('{plan_path}', sys.argv[1])\""
    
    env = os.environ.copy()
    env["GIT_SEQUENCE_EDITOR"] = sequence_editor

    try:
        subprocess.run(["git", "rebase", "-i", base], env=env, check=True)
        typer.secho("Rebase completed successfully!", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("Rebase failed. You may need to resolve conflicts manually.", fg=typer.colors.RED)
        typer.secho("Run 'git rebase --abort' if you want to cancel.", fg=typer.colors.YELLOW)
    finally:
        if os.path.exists(plan_path):
            os.remove(plan_path)

@app.command(name="pr")
def create_pr(
    base: str = typer.Option("main", "-b", "--base", help="Base branch for the Pull Request."),
    provider: str = typer.Option(None, "-p", "--provider", help="AI provider to use."),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Preview without creating PR.")
):
    """Generate a Pull Request description and optionally create it via GitHub CLI."""
    if not shutil.which("git"):
        typer.secho("Git not found!", fg=typer.colors.RED)
        sys.exit(1)

    # 1. Get commits log and diff
    try:
        log_output = subprocess.check_output(
            ["git", "log", f"{base}..HEAD", "--pretty=format:- %s%n%b"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        diff_output = subprocess.check_output(
            ["git", "diff", f"{base}...HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        )
    except subprocess.CalledProcessError:
        typer.secho(f"Could not analyze changes between {base} and HEAD.", fg=typer.colors.RED)
        sys.exit(1)

    if not log_output:
        typer.secho(f"No commits ahead of {base}.", fg=typer.colors.YELLOW)
        sys.exit(0)

    # 2. Select provider
    provider_name = provider or config_mgr.get_default_provider()
    provider_cfg = config_mgr.get_provider_config(provider_name)

    typer.echo(f"Analyzing {len(log_output.splitlines())} lines of history to write PR description...")

    # 3. Generate PR Description
    system_prompt = (
        "You are a Senior Developer writing a Pull Request description.\n"
        "I will provide you with the commit messages and the diff of the changes.\n"
        "Generate a structured Markdown PR description.\n"
        "Include these sections:\n"
        "## Title (first line should just be the title string without ##)\n"
        "## Motivation and Context\n"
        "## What changed\n"
        "## Testing Instructions\n"
        "Keep it concise, professional, and do not output any surrounding ```markdown blocks."
    )

    # Truncate diff if it's too large (very simple heuristic to save tokens)
    if len(diff_output) > PR_MAX_DIFF_LENGTH:
        diff_output = diff_output[:PR_MAX_DIFF_LENGTH] + "\n... (diff truncated)"

    prompt_text = f"Commits:\n{log_output}\n\nDiff:\n{diff_output}"

    try:
        ai = AIProvider(provider_name, provider_cfg)
        pr_description = ai.execute(prompt_text, system_prompt=system_prompt)
    except Exception as e:
        typer.secho(f"\nAI Error: {str(e)}", fg=typer.colors.RED)
        sys.exit(1)
        
    pr_description = re.sub(r'^```[a-zA-Z]*\n', '', pr_description)
    pr_description = pr_description.replace('```', '').strip()

    # The first line is typically the PR title
    lines = pr_description.split('\n')
    pr_title = lines[0].replace('## Title', '').replace('# ', '').strip()
    if pr_title.startswith(':'):
        pr_title = pr_title[1:].strip()
    pr_body = '\n'.join(lines[1:]).strip()

    typer.echo("\n--- Generated Pull Request ---")
    typer.echo(f"Title: {pr_title}")
    typer.echo("Body:")
    typer.echo(pr_body)
    typer.echo("------------------------------")

    if dry_run:
        sys.exit(0)

    # 4. Ask to create PR using GitHub CLI
    if shutil.which("gh"):
        if typer.confirm("Create Pull Request via GitHub CLI (gh)?", default=True):
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(pr_body)
                body_path = f.name
            
            try:
                subprocess.run(["gh", "pr", "create", "--base", base, "--title", pr_title, "--body-file", body_path], check=True)
                typer.secho("Pull Request created successfully!", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho("Failed to create PR via GitHub CLI.", fg=typer.colors.RED)
            finally:
                if os.path.exists(body_path):
                    os.remove(body_path)
    else:
        typer.secho("\nGitHub CLI (gh) not installed. Please copy the text above to create your PR manually.", fg=typer.colors.YELLOW)

@app.command(name="stats")
def stats_cmd(
    reset: bool = typer.Option(False, "--reset", help="Clear usage statistics."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON data.")
):
    """Display usage statistics."""
    if reset:
        if clear_stats():
            typer.secho("Statistics cleared.", fg=typer.colors.GREEN)
        else:
            typer.secho("Failed to clear statistics.", fg=typer.colors.RED)
        return

    stats = load_stats()
    if not stats:
        if json_output:
            print(json.dumps({}))
        else:
            typer.echo("No statistics recorded yet. Generate some commit messages first!")
        return

    if json_output:
        print(json.dumps(stats, indent=2))
        return

    # Visual display
    attempts = stats.get("generated_attempts", 0)
    decisions = stats.get("decisions", {})
    accepted = decisions.get("accepted", 0)
    rejected = decisions.get("rejected", 0)
    rate = round((accepted / (accepted + rejected) * 100)) if (accepted + rejected) > 0 else 0
    
    typer.echo("Git-Sensei Statistics")
    typer.echo("──────────────────────")
    typer.echo(f"Commits generated:  {attempts}")
    typer.echo(f"Acceptance rate:    {rate}% ({accepted} accepted, {rejected} rejected)")
    
    # Providers breakdown
    providers = stats.get("providers", {})
    if providers:
        prov_parts = []
        for name, count in providers.items():
            pct = round((count / attempts) * 100) if attempts > 0 else 0
            prov_parts.append(f"{name} ({pct}%)")
        typer.echo(f"Provider usage:     {', '.join(prov_parts)}")
        
    # Types distribution
    types = stats.get("types", {})
    if types:
        sorted_types = sorted(types.items(), key=lambda x: x[1], reverse=True)
        type_parts = []
        for t_name, count in sorted_types[:3]:
            pct = round((count / attempts) * 100) if attempts > 0 else 0
            type_parts.append(f"{t_name} ({pct}%)")
        typer.echo(f"Most common type:   {', '.join(type_parts)}")
        
    typer.echo(f"Average msg length: {stats.get('average_message_length', 0)} chars")


@app.command(name="lint")
def lint_cmd(
    message: Optional[str] = typer.Argument(None, help="Commit message string or path to a commit message file.")
):
    """Lint commit message formatting for Conventional Commits."""
    msg = ""
    if message:
        if os.path.exists(message):
            try:
                with open(message, "r", encoding="utf-8") as f:
                    msg = f.read()
            except Exception as e:
                typer.secho(f"Error reading file '{message}': {e}", err=True, fg=typer.colors.RED)
                sys.exit(1)
        else:
            msg = message
    else:
        # Check if stdin has data
        if not sys.stdin.isatty():
            msg = sys.stdin.read()
        else:
            typer.secho("Error: No commit message provided to lint.", err=True, fg=typer.colors.RED)
            typer.echo("Usage: sensei lint 'feat: my commit message' or sensei lint .git/COMMIT_EDITMSG", err=True)
            sys.exit(1)

    errors = []
    lines = msg.strip().splitlines()
    if not lines:
        errors.append("Commit message is empty.")
    else:
        first_line = lines[0].strip()
        
        # Check Conventional Commits standard
        pattern = r"^(?::\w+:|[\U00010000-\U0010ffff]\s*)?\s*(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\([^)]+\))?!?\s*:\s*.+$"
        if not re.match(pattern, first_line):
            errors.append("First line does not match Conventional Commits format (e.g. 'feat(scope): add feature').")
            
        # Check first line length
        if len(first_line) > 72:
            errors.append(f"First line exceeds 72 characters ({len(first_line)} chars).")
            
        # Check disallowed markdown
        if "`" in first_line or "**" in first_line or "*" in first_line:
            errors.append("First line contains disallowed markdown formatting (backticks, bold, italic).")

    if errors:
        typer.secho("✗ Commit message validation failed:", err=True, fg=typer.colors.RED)
        for err in errors:
            typer.secho(f"  - {err}", err=True, fg=typer.colors.RED)
        sys.exit(1)
        
    typer.secho("✓ Commit message is valid.", fg=typer.colors.GREEN)
    sys.exit(0)


@app.command(name="log")
def log_cmd(
    count: int = typer.Option(10, "-n", "--count", help="Number of commits to display."),
    all_history: bool = typer.Option(False, "--all", help="Display full commit history."),
    stats: bool = typer.Option(False, "--stats", help="Show commit type distribution summary.")
):
    """Display colored commit history with Conventional Commits validation."""
    limit = -1 if all_history else count
    log_args = ["git", "log", "--no-merges", "--format=%h %B===COMMIT_DELIMITER==="]
    if limit > 0:
        log_args.append(f"-{limit}")
        
    try:
        res = subprocess.run(log_args, capture_output=True, text=True, encoding="utf-8", check=True)
        raw_log = res.stdout
    except Exception as e:
        typer.secho(f"Error running git log: {e}", fg=typer.colors.RED)
        sys.exit(1)
        
    commits_raw = raw_log.split("===COMMIT_DELIMITER===")
    commits = []
    for c in commits_raw:
        c_strip = c.strip()
        if c_strip:
            parts = c_strip.split(" ", 1)
            hash_str = parts[0]
            msg = parts[1] if len(parts) > 1 else ""
            commits.append((hash_str, msg))
            
    if not commits:
        typer.echo("No commits found.")
        return

    type_counts = {}
    valid_count = 0
    total_count = len(commits)

    pattern = r"^(?::\w+:|[\U00010000-\U0010ffff]\s*)?\s*(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\((?P<scope>[^)]+)\))?!?\s*:\s*(?P<subject>.+)$"

    for hash_str, msg in commits:
        first_line = msg.strip().splitlines()[0] if msg.strip() else ""
        match = re.match(pattern, first_line)
        
        color = typer.colors.WHITE
        is_valid = False
        display_type = "unknown"
        display_scope = ""
        display_subject = first_line

        if match:
            is_valid = len(first_line) <= 72 and not ("`" in first_line or "**" in first_line)
            display_type = match.group("type")
            display_scope = match.group("scope") or ""
            display_subject = match.group("subject")
            
            type_counts[display_type] = type_counts.get(display_type, 0) + 1
            
            color_map = {
                "feat": typer.colors.GREEN,
                "fix": typer.colors.RED,
                "docs": typer.colors.BLUE,
                "refactor": typer.colors.YELLOW,
                "style": typer.colors.MAGENTA,
                "perf": typer.colors.CYAN,
                "test": typer.colors.CYAN,
                "build": typer.colors.CYAN,
                "ci": typer.colors.CYAN,
                "chore": typer.colors.CYAN,
                "revert": typer.colors.CYAN
            }
            color = color_map.get(display_type, typer.colors.WHITE)
            
        if is_valid:
            valid_count += 1
            status_marker = typer.style("✓", fg=typer.colors.GREEN)
        else:
            status_marker = typer.style("✗", fg=typer.colors.RED)
            
        hash_styled = typer.style(hash_str, fg=typer.colors.BRIGHT_BLACK)
        type_styled = typer.style(display_type, fg=color, bold=True)
        scope_styled = f"({typer.style(display_scope, fg=typer.colors.MAGENTA)})" if display_scope else ""
        
        if match:
            typer.echo(f"* {hash_styled} {type_styled}{scope_styled}: {display_subject}  {status_marker}")
        else:
            typer.echo(f"* {hash_styled} {typer.style(first_line, fg=typer.colors.BRIGHT_BLACK)}  {status_marker}")

    if stats and total_count > 0:
        typer.echo("\nCommit Type Distribution:")
        typer.echo("──────────────────────────")
        for t_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / total_count) * 100)
            typer.echo(f"  {t_name}: {count} ({pct}%)")
        typer.echo("──────────────────────────")
        valid_pct = round((valid_count / total_count) * 100)
        typer.echo(f"Conventional Commits compliance: {valid_count}/{total_count} ({valid_pct}%)")


if __name__ == "__main__":
    app(prog_name="sensei")
