# Git-Sensei

> **Smart Context. Universal AI Adapter. Professional Commits.**

A CLI tool that generates professional commit messages using any AI provider (Gemini, Claude Code, OpenAI, Ollama).

## Features

- **Universal Providers** - Switch between Gemini, Claude Code, OpenAI, or local LLMs with one command
- **Smart Context** - Automatically links commits to Jira/issue IDs from branch names (e.g., `PROJ-123`)
- **Conventional Commits** - Generates properly formatted commit messages
- **Offline Fallback** - Heuristic engine works when AI is unavailable
- **Interactive Review** - Edit, retry, or approve before committing

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/git-sensei.git
cd git-sensei

# Install dependencies
pip install typer

# (Optional) Install as global command
pip install -e .
```

## Requirements

- **Python 3.9+**
- **Git**
- **One of the AI CLI tools:**

| Provider | Installation |
|----------|-------------|
| Gemini | `npm install -g @google/gemini-cli` |
| Claude Code | `npm install -g @anthropic-ai/claude-code` |
| OpenAI | `pip install chatgpt-cli` |
| Ollama | [ollama.ai](https://ollama.ai) |

## Quick Start

```bash
# Stage your changes
git add .

# Generate commit message
sensei commit

# Or with a specific provider
sensei commit --provider claude
```

## Commands

| Command | Description |
|---------|-------------|
| `sensei commit` | Generate and create a commit |
| `sensei use <provider>` | Set default AI provider |
| `sensei ls` | List available providers |
| `sensei check [provider]` | Verify provider is working |

### Examples

```bash
# Set Claude Code as default
sensei use claude

# List providers (* marks default)
sensei ls

# Check if provider works
sensei check claude

# Dry run (preview without committing)
sensei commit --dry-run
```

## Configuration

Sensei loads configuration from (in order of priority):
1. `~/.sensei.toml` (user config - highest priority)
2. `./.sensei.toml` (project config)
3. Package defaults

### Example `.sensei.toml`

```toml
[core]
default_provider = "claude"

[providers.gemini]
description = "Google Gemini CLI"
command = "gemini \"{system}\""

[providers.claude]
description = "Claude Code CLI"
command = "claude --print \"{system}\""

[providers.openai]
description = "OpenAI GPT-4"
command = "chatgpt -m gpt-4 --system \"{system}\""

[providers.local]
description = "Local AI (Ollama)"
command = "ollama run llama3 \"{system}\""
```

The `{system}` placeholder is replaced with the prompt. Git diff is piped to stdin.

## Interactive Workflow

After generating a message, you'll see:

```
--------------------------------------------------
Suggested: feat(auth): add user login endpoint
--------------------------------------------------
Action? [y]es, [n]o, [e]dit, [r]etry
```

- **y** - Commit with this message
- **n** - Abort
- **e** - Edit the message
- **r** - Regenerate with AI

## Project Structure

```
git_sensei/
├── main.py           # CLI entrypoint
├── config.py         # Configuration loader
├── providers.py      # AI provider adapter
├── local_bridge.py   # Offline fallback engine
├── .sensei.toml      # Default configuration
├── tests/            # Unit tests
└── docs/             # Documentation
```

## Changelog

<details>
<summary>Version history</summary>

### v0.7.0 (2025-12-30)
- Added `sensei use <provider>` command
- User config now takes priority over project config
- Added Claude Code CLI support

### v0.6.0 (2025-12-18)
- Windows support for `.cmd` and `.bat` tools
- Enforced `sensei commit` as primary command

### v0.5.0 (2025-12-18)
- Universal AI Adapter - works with any CLI tool
- Added `.sensei.toml` configuration
- Added `sensei check` and `sensei ls` commands

### v0.4.0 (2025-12-18)
- Smart Context - auto-detect issue IDs from branch names

### v0.3.0 (2025-12-18)
- Inline message editing

### v0.2.0 (2025-12-17)
- Gemini CLI integration

### v0.1.0 (2025-12-09)
- Initial release with heuristic engine

</details>

## License

MIT
