# Git-Sensei

> **Smart Context. Universal AI Adapter. Professional Commits.**

A CLI tool that generates professional commit messages using any AI provider (Gemini, Claude Code, OpenAI, Ollama).

## Features

- **Universal Providers** - Switch between Gemini, Claude Code, OpenAI, or local LLMs with one command
- **Secrets Shield** - Scans diffs for API keys, tokens, passwords before sending to AI
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
sensei init      # First time setup (choose AI provider)
git add .        # Stage your changes
sensei commit    # Generate commit with AI
```

## Commands

| Command | Description |
|---------|-------------|
| `sensei init` | Interactive setup wizard |
| `sensei commit` | Generate and create a commit |
| `sensei commit -p claude` | Use specific provider |
| `sensei commit -d` | Dry run (preview only) |
| `sensei use <provider>` | Set default AI provider |
| `sensei ls` | List available providers |
| `sensei check [provider]` | Verify provider is working |
| `sensei hook` | Install git hook for auto-generation |
| `sensei hook -u` | Uninstall git hook |

### Examples

```bash
sensei commit                 # Use default provider
sensei commit -p claude       # Use Claude for this commit
sensei commit -d              # Preview without committing
sensei use claude             # Set Claude as default
sensei ls                     # List providers (* = default)
sensei check                  # Check default provider
sensei check claude           # Check specific provider
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

### v0.10.0 (2025-12-30)
- Added `sensei hook` - install git hook for automatic message generation
- Now `git commit` can auto-generate messages

### v0.9.0 (2025-12-30)
- Added Secrets Shield - detects API keys, tokens, passwords in diffs
- Warns before sending sensitive data to AI provider

### v0.8.0 (2025-12-30)
- Added `sensei init` interactive setup wizard
- Improved CLI help messages with examples

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
