# 🥋 Git-Sensei

> **Smart Context. Universal AI Adapter. Professional Commits.**
> 
> An automated commit message generator that orchestrates **ANY AI CLI** (Gemini, Claude, OpenAI, Ollama) to analyze your code and write professional logs.

---

## 🧐 What is it?

**Git-Sensei** is a "Meta-CLI" tool designed to eliminate "Commit Fatigue".
It reads your staged changes (`git diff`) and pipes them through your preferred AI engine to understand *why* you made the changes.

**Key Philosophy:**
*   **Universal Adapter:** Works with *any* CLI tool you have installed (Gemini, Claude, GitHub Copilot, custom scripts).
*   **Bring Your Own Auth (BYOA):** We don't manage your keys. If your CLI works in the terminal, it works with Sensei.
*   **Privacy Choice:** Use cloud AI for power, or local LLMs (Ollama) for privacy.

## 🚀 Features

- **🔌 Universal Providers:** Switch between Gemini, Claude, or Local Llama with one config change.
- **🧠 Context Aware:** Understands complex refactoring and generates detailed commit bodies.
- **🎫 Smart Context:** Automatically links commits to tasks by extracting IDs (e.g., `PROJ-123`) from branch names.
- **⚡ Offline Fallback:** Zero latency mode when AI is unreachable.
- **🛡️ Safety Net:** Nothing is committed without your explicit `[y/N]` confirmation.

## 🛠️ Requirements

1.  **Python 3.9+** & **Git**
2.  **Any AI CLI Tool** (Optional but recommended):
    - `npm install -g @google/gemini-cli`
    - `pip install llm` (for Claude/GPT)
    - `ollama` (for local models)

## 💻 Usage

### 1. Basic Workflow
Stage your changes and run the sensei:
```bash
git add .
sensei
```

### 2. Switching Providers
Want to use a specific model for a tough task?
```bash
# List available providers from your config
sensei ls           # (alias for list-providers)

# Use a specific one
sensei commit --provider claude
```

### 3. Diagnostics
Check if your configured tools are reachable:
```bash
sensei doctor       # (alias for check)
sensei check --provider claude
```

## ⚙️ Configuration (`.sensei.toml`)

Sensei looks for a configuration file in the project root or `~/.sensei.toml`.
Use this to define your own wrappers!

```toml
[core]
default_provider = "gemini"

[providers.gemini]
description = "Google Gemini"
command = "gemini --system \"{system}\""

[providers.claude]
description = "Anthropic Claude via 'llm' tool"
command = "llm -m claude-3-opus -s \"{system}\""
```

---

## 📂 Project Structure

```text
git_sensei/
├── main.py           # CLI Entrypoint & UI
├── config.py         # TOML Configuration Loader
├── providers.py      # Universal Command Adapter
├── local_bridge.py   # Offline Heuristic Engine
├── .sensei.toml      # Default configuration
└── docs/             # ADRs, Roadmap & Deep Research
```

---

## 📜 Changelog

<details>
<summary><strong>Click to expand version history</strong></summary>

### v0.6.0 (2025-12-18) - The Final Universal Polish
*   **feat(win32):** Added support for `.cmd` and `.bat` AI CLI tools (like npm globals) via `shell=True`.
*   **feat(cli):** Enforced `sensei commit` as the primary action for better CLI clarity.
*   **feat(ux):** Improved help messages with `prog_name="sensei"` for cleaner terminal output.
*   **fix(config):** Adjusted default `.sensei.toml` for compatibility with `@google/gemini-cli`.

### v0.5.1 (2025-12-18)
*   **refactor:** Flattened project structure for better maintainability.
*   **feat(cli):** Added short aliases for common commands (`ls` for `list-providers`, `doctor` for `check`).
*   **docs:** Moved architectural documents to `docs/`.

### v0.5.0 (2025-12-18) - The Universal Update
*   **feat(core):** Implemented **Universal AI Adapter**. Sensei is now agnostic and can drive any CLI tool defined in configuration.
*   **feat(config):** Added `.sensei.toml` support for defining custom providers and commands.
*   **feat(cli):** Added `sensei check` for diagnosing tool availability.
*   **feat(cli):** Added `sensei list-providers` to show available engines.
*   **feat(ux):** Added `[r]etry` option to the commit review menu.

### v0.4.0 (2025-12-18)
*   **feat(core):** Implemented Smart Context. The tool now automatically detects issue IDs (like `PROJ-123`) from branch names and appends `Refs: ID` to the commit footer.

### v0.3.0 (2025-12-18)
*   **feat(ux):** Added inline message editing. Press `e` to tweak the suggestion directly in the terminal.
*   **style(ai):** Enforced stricter prompt rules.

### v0.2.0 (2025-12-17)
*   **feat(core):** Integrated `gemini-cli` pipe.

### v0.1.0 (2025-12-09)
*   **feat:** Initial release with Heuristic Logic Engine.

</details>

---

_Built for productivity and clean code enthusiasts._