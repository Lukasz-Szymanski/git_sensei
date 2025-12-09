# 🥋 Git-Sensei

> **Stop writing "fix". Start understanding your history.**
> An intelligent CLI wrapper for Git that uses Google Gemini to generate semantic, Conventional Commits messages automatically.

---

## 🧐 What is it?

**Git-Sensei** is a Python-based CLI tool designed to solve "Commit Fatigue". Instead of staring at a blinking cursor trying to summarize your changes, Git-Sensei:

1.  Reads your staged changes (`git diff --staged`).
2.  Sends them to **Google Gemini 3 Pro**.
3.  Generates a message strictly adhering to **Conventional Commits** (e.g., `feat(auth): add jwt validation`).
4.  **Validates** the output using Regex to ensure quality.
5.  Commits the changes only after your approval.

## 🚀 Features

- **AI-Powered Analysis:** Uses Gemini 3 Pro to understand _what_ you changed and _why_.
- **Strict Standardization:** Enforces [Conventional Commits v1.0.0](https://www.conventionalcommits.org/).
  - Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
- **Guardrails:** Built-in Regex validation ensures the AI doesn't produce garbage.
- **Safety Net:** Nothing is committed without your explicit `[y/N]` confirmation.

## 🛠️ Prerequisites

To run Git-Sensei, you need:

1.  **Python 3.9+** installed.
2.  **Git** installed and initialized in your project.
3.  **gemini-chat CLI**: This tool currently acts as a wrapper around the `gemini-chat` command line interface. You must have it installed and available in your system PATH.
    - _Note: Future versions will integrate the Google SDK directly._

## 📦 Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Lukasz-Szymanski/git_sensei.git
    cd git_sensei
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install typer
    ```

## 💻 Usage

1.  **Stage your changes** (Git-Sensei only looks at staged files):

    ```bash
    git add .
    ```

2.  **Run the Sensei:**

    ```bash
    python main.py
    ```

3.  **Review & Confirm:**
    - If the message looks good, type `y` and press Enter.
    - If not, type `n` to abort.

## 🤖 Technical Context (For AI Agents)

- **Architecture:** Python `subprocess` wrapper.
- **Core Logic:** `main.py` executes `git diff`, pipes stdout to `gemini-chat`, captures stdout, validates via `re` module, and executes `git commit`.
- **Stack:** Python, Typer (CLI), Subprocess (Shell interaction).
- **Prompt Strategy:** System prompt enforces "raw text output" and "no markdown" to ensure clean pipe processing.

---

_Created by Łukasz Szymański_
