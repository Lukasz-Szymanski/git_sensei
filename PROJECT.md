# Project: Git-Sensei Production Hardening

## Architecture
Git-Sensei is a Python CLI built on `typer`. It interacts with Git via `subprocess` calls and communicates with AI providers (OpenAI, Gemini, etc.) using native HTTP calls or local wrappers.
- `main.py`: Entrypoint, command line interface and interactive loop.
- `config.py`: Configuration manager for project and user-level `.sensei.toml` configurations.
- `git_utils.py`: Git operations, diff extraction, and commit logic.
- `providers.py`: Integration with OpenAI and Gemini API endpoints.
- `secrets_shield.py`: Scanning diffs for sensitive patterns (passwords, api keys).
- `local_bridge.py`: Local heuristics for generating commit messages when AI is offline.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Custom Prompts & Few-Shot History | Support prompt customization, few-shot logging, languages, emojis, line length | None | COMPLETED |
| 2 | Smart Truncation & Filtering | Token budget, lockfile skip/summarize, smart strategies (smart, head, tail, sample) | M1 | COMPLETED |
| 3 | Monorepo Scope Auto-Detection | Match directory structure and globs to conventional commit scopes | M1 | PLANNED |
| 4 | Interactive Selector & Refinement | Type/emoji interactive selector, text refinement loop for commit messages | M1 | PLANNED |
| 5 | Atomic Diff Splitter | Split staged diff into multiple commits, interactive staging/committing | M2, M4 | PLANNED |
| 6 | Custom API Endpoints & Redaction | OpenAI-compatible custom API support, auto-redacting secrets in diffs with [REDACTED] | M2 | PLANNED |
| 7 | CLI Diagnostics & Pre-commit Hook | Commands `sensei stats`, `sensei log`, `sensei lint` and `.pre-commit-hooks.yaml` config | M4 | PLANNED |

## Interface Contracts

### 1. Prompt Configuration (config.py ↔ main.py)
`ConfigManager` must expose:
- `get_universal_prompt(self) -> str`
- `get_prompt_config(self) -> dict` (returns language, style, max_length, template, and custom prompts)
`git_utils.py` must expose:
- `get_recent_commits(count: int = 5) -> List[str]` to fetch few-shot logs.

### 2. Truncation Manager (git_utils.py ↔ main.py)
`git_utils.py` must expose:
- `get_staged_diff_filtered(config: dict) -> Tuple[Optional[str], dict]` where filtered diff and a dict of skipped/summarized files are returned.
`config.py` must expose truncation token settings under `truncation` section.

### 3. Monorepo Scoper (local_bridge.py ↔ git_utils.py ↔ config.py)
`git_utils.py` must expose:
- `detect_monorepo_scope(changed_files: List[str], monorepo_config: dict) -> Optional[str]`
Glob matching should use standard library `fnmatch`.

### 4. Refinement & Selection (main.py)
Main review loop handles `[y]es, [n]o, [e]dit, [r]etry` and additions:
- `[r]efine`: prompts user for refinement text, calls AI execution with prior suggestion + text.
- `[s]elect`: interactive cli prompt (such as simple list selector) for commit type and emoji.

### 5. Multi-commit Splitter (git_utils.py ↔ main.py)
`git_utils.py` must expose:
- `split_staged_diff(diff: str) -> List[dict]` where each group contains list of files and suggested message.
`main.py` implements interactive staging flow.

### 6. OpenAI-Compatible Custom Provider (providers.py ↔ config.py)
`AIProvider` handles:
- Config keys `api_url` and `api_key_env`.
`secrets_shield.py` exposes:
- `redact_secrets(diff: str, custom_patterns: dict = None) -> str` returning diff with secrets replaced by `[REDACTED]`.

### 7. Stats & Log & Lint CLI Commands (main.py ↔ config.py)
Commands:
- `@app.command()` `stats` -> tracks stats in `~/.sensei/stats.json`.
- `@app.command()` `log` -> prints formatted git log.
- `@app.command()` `lint` -> checks conventional commit message format.

## Code Layout
- `main.py`: Entrypoint and Typer commands.
- `config.py`: Toml parser and config manager.
- `providers.py`: API provider wrappers.
- `git_utils.py`: Git connector.
- `secrets_shield.py`: Secret scanning and redaction.
- `local_bridge.py`: Fallback offline generator.
- `tests/`: Unit test suite.
- `.pre-commit-hooks.yaml`: Pre-commit hook configuration.
