# 🥋 Git-Sensei (Offline Edition)

> **Zero Latency. Zero Tokens. 100% Conventional Commits.**
>
> An automated commit message generator that **doesn't use AI**, works instantly, and ensures your project history stays clean.

---

## 🧐 What is it?

**Git-Sensei** is a Python-based CLI tool designed to eliminate "Commit Fatigue". Instead of manually typing lazy messages like `git commit -m "fix things"`, Sensei analyzes your changes (`git diff`) and uses a **Heuristic Logic Engine** to generate a perfectly formatted message following the **Conventional Commits** specification.

**The Key Difference:** This tool is 100% offline. It doesn't send your code to the cloud (Google/OpenAI), requires no API keys, and runs in milliseconds.

## 🚀 Features

- **⚡ Blazing Fast:** No network latency. Analysis is performed locally.
- **🔒 Private:** Your code never leaves your machine.
- **💰 Zero Cost:** No LLM token usage or subscriptions.
- **📏 Standardization:** Enforces the `type(scope): description` format.
  - Supported types: `feat`, `fix`, `docs`, `style`, `test`, `chore`.
- **🛡️ Safety Net:** Nothing is committed without your explicit `[y/N]` confirmation.
- **🔄 Automation:** Optionally executes `git push` after a successful commit.

## 🧠 How it Works (Heuristic Engine)

Instead of a neural network, we use a smart logic script (`local_bridge.py`) that analyzes staged files:

1.  **Type Detection:**
    - Changes in `.py`, `.js`, `.go`, etc. → **`feat`**
    - Changes in `.md`, `.txt` → **`docs`**
    - Changes in `.css`, `.scss` → **`style`**
    - Changes in `.gitignore`, `package.json` → **`chore`**
    - Detection of keywords like "fix", "bug", or "error" in code → Forces **`fix`**
2.  **Scope Determination:**
    - Automatically extracts the name of the primary modified file (e.g., `main.py` → `main`).
3.  **Description Generation:**
    - Creates a template based on the action (e.g., "implement logic in main", "update docs in README").

## 🛠️ Requirements & Installation

You only need **Python 3.9+** and **Git**.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YourUsername/git_sensei.git
    cd git_sensei
    ```

2.  **Install the lightweight CLI dependency:**
    ```bash
    pip install typer
    ```

## 💻 Usage

1.  **Stage your changes:** (Sensei only sees what's in the staging area!)
    ```bash
    git add .
    ```

2.  **Run the Sensei:**
    ```bash
    python main.py
    ```

3.  **Confirm:**
    The program will display a proposal:
    ```text
    Suggested Commit: feat(local_bridge): implement logic in local_bridge.py
    ```
    - Type `y` and press Enter to commit.
    - The program will also ask if you want to `git push`.

## 📂 Project Structure

```text
git_sensei/
├── main.py           # Main CLI interface (Typer-based)
├── local_bridge.py   # Logic engine (Diff analysis, text generation)
└── README.md         # Documentation
```

---

_Built for productivity and clean code enthusiast._