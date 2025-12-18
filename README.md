# 🥋 Git-Sensei

> **Smart Context. Professional Commits. Hybrid Engine.**
>
> An automated commit message generator that leverages **Google Gemini CLI** for deep code analysis, with a blazing fast **Offline Fallback** when you are off the grid.

---

## 🧐 What is it?

**Git-Sensei** is a Python-based CLI tool designed to eliminate "Commit Fatigue".
It reads your staged changes (`git diff`) and pipes them through an AI engine to understand *why* you made the changes, not just *what* changed.

**Hybrid Architecture:**
1.  **Online (Primary):** Uses `gemini-cli` to generate human-like, context-aware descriptions.
2.  **Offline (Backup):** Automatically switches to a Heuristic Logic Engine if no internet/AI is available.

## 🚀 Features

- **🧠 Context Aware:** Understands complex refactoring and generates detailed commit bodies.
- **⚡ Blazing Fast Fallback:** Zero latency mode when AI is unreachable.
- **🔒 Privacy First:** Your code is processed via your local CLI configuration.
- **📏 Standardization:** Enforces **Conventional Commits** (`feat`, `fix`, `chore`, etc.).
- **🛡️ Safety Net:** Nothing is committed without your explicit `[y/N]` confirmation.

## 🛠️ Requirements

1.  **Python 3.9+** & **Git**
2.  **Gemini CLI** (optional, for AI features)
    - Install via npm: `npm install -g @google/gemini-cli` (or similar provider)

## 💻 Usage

1. **Stage your changes:**
   ```bash
   git add .
   ```

2. **Run the Sensei:**

   **Option A: Direct Execution**
   ```bash
   python main.py
   ```

   **Option B: Global Command**
   ```bash
   sensei
   ```
   *(Requires adding the script to your `PATH` or creating an alias)*

3. **Review & Decide:**
    ```text
    Suggested: feat(auth): implement JWT token validation

    [Body]
    - added middleware for token extraction
    - updated user model to store refresh tokens
    
    Action? [y]es, [n]o, [e]dit [y]:
    ```
    *   **[y]es:** Commit and push (optional).
    *   **[e]dit:** Tweak the message inline without leaving the terminal.
    *   **[n]o:** Abort.

## 📂 Project Structure

```text
git_sensei/
├── main.py           # Core Logic & AI Pipe
├── local_bridge.py   # Offline Heuristic Engine
└── FUTURE_CLI_IDEAS.md # Roadmap
```

---

## 📜 Changelog

<details>
<summary><strong>Click to expand version history</strong></summary>

### v0.3.0 (2025-12-18)
*   **feat(ux):** Added inline message editing. Press `e` to tweak the suggestion directly in the terminal.
*   **style(ai):** Enforced stricter prompt rules to ban first-person references ("I", "we") and ensure imperative mood.
*   **chore:** Setup local testing environment in `.gitignore`.

### v0.2.0 (2025-12-17)
*   **feat(core):** Integrated `gemini-cli` pipe for intelligent, context-aware commit messages.
*   **style(prompt):** Configured AI to generate detailed body descriptions for complex logic changes (not just one-liners).
*   **refactor(bridge):** Translated all internal logic and comments in `local_bridge.py` to English for better maintainability.
*   **fix(win32):** Improved subprocess handling for Windows environments.
*   **chore:** Moved `sensei.bat` outside the repo for cleaner project structure.

### v0.1.0 (2025-12-09)
*   **feat:** Initial release with Heuristic Logic Engine.
*   **feat:** Basic `type(scope): description` formatting.

</details>

---

_Built for productivity and clean code enthusiasts._
