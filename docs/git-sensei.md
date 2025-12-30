# 🥋 Git-Sensei: MVP Project Brief

> **Tagline:** _Stop writing "fix" commits. Start understanding Git._

---

## 1. Pain Points (Co boli?)

- **Messy Project History:** Developers often use meaningless commit messages (e.g., _"wip"_, _"fix"_, _"changes"_) due to laziness or lack of time, making the history unreadable.
- **Context Switching:** Manually analyzing `git diff` to write a good summary breaks the coding "flow" and forces the developer to switch context.
- **Junior Anxiety:** Beginners struggle with naming conventions (Conventional Commits) and fear criticism for "bad" logs.

## 2. Target Audience (Dla kogo?)

Junior to Mid-level Developers who want to maintain a professional git history (Clean Code) but lack the discipline or experience to do it manually every time.

## 3. Why CLI? (Dlaczego CLI?)

- **Zero Context Switching:** It allows developers to stay in their natural environment (terminal) without switching to a browser/web UI.
- **Unix Philosophy:** It enables easy integration with existing system tools via **pipes** (e.g., `git diff | sensei`).

---

## 4. Core MVP Functionality (Step-by-Step)

_The absolute minimum scope to solve the problem._

1.  **Check:** Script verifies if the staging area is not empty (`git diff --staged --quiet`). If empty, it exits immediately.
2.  **Fetch:** Captures the changes using `git diff --staged`.
2.  **Process:** Pipes the diff to the external **Gemini CLI** tool (passing `--model "gemini-3-pro"`).
4.  **Display:** Prints the raw commit message proposal (simple text, no styling).
5.  **Decision:** Prompts the user: `Commit with this message? [y/N]`.
6.  **Action:**
    - If `y`: Executes `git commit -m "message"`.
    - If `N`: Aborts the operation (safety net).

---

## 5. Technology Stack

- **Language:** Python 3.9+ (acting as system "glue code").
- **Libraries:**
  - `subprocess` (STDLIB): For executing Git commands and handling standard streams (pipes).
  - `shutil` (STDLIB): For verifying tool existence (`which`).
  - `typer` (EXTERNAL): The only external dependency, used for clean CLI argument parsing.
- **System Dependencies:** User must have `git` and `gemini-chat-cli` installed and configured.

---

## 6. Business Edge Cases & Risks

_Focusing on user value and safety, not just exceptions._

1.  **AI Hallucination Risk:** The AI might suggest a commit message that contradicts the actual code (e.g., claiming a feature was added when it was removed).
    - _Solution:_ The tool is **never** fully autonomous. The user MUST explicitly type `y` to confirm. This is the primary "Safety Net".
2.  **User Rejection:** The AI suggestion is factually correct but stylistically wrong for the user.
    - _Solution:_ The tool allows a quick abort (`N`), letting the user fall back to manual `git commit` without friction.
3.  **Large Diff Context:** The user stages a massive file (e.g., 5000 lines), potentially confusing the model or hitting token limits.
    - _Solution:_ The script should detect massive diffs and warn the user that the summary might be less accurate, managing expectations.

---

## 7. Out of Scope (Not in MVP)

- `sensei status` feature (Education layer moved to v2.0).
- Message editing mode inside the app (Binary choice only: Yes/No).
- Syntax highlighting/spinners (No `rich` library to reduce dependencies).
- Handling `.env` files (Relies on global user environment).

---

## 8. System Prompt (Embedded)

_Instruction passed to `gemini-chat-cli` via pipe:_

> "You are a Senior DevOps Engineer. Analyze the provided code diff. Generate a SINGLE commit message strictly following the **Conventional Commits v1.0.0** specification.
> Format: `<type>(<scope>): <description>`
> Output ONLY the raw message string. No markdown, no explanations."
