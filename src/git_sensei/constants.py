"""Shared constants for git_sensei."""
import re

# Conventional commit types
COMMIT_TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]

# Gitmoji mapping - the SINGLE source of truth
GITMOJI_MAP = {
    "feat": "✨",
    "fix": "🐛",
    "docs": "📝",
    "style": "🎨",
    "refactor": "♻️",
    "perf": "⚡️",
    "test": "🧪",
    "build": "📦",
    "ci": "💚",
    "chore": "🔧",
    "revert": "⏪",
}

# Commit type color mapping for CLI display
TYPE_COLOR_MAP = {
    "feat": "green",
    "fix": "red",
    "docs": "blue",
    "refactor": "yellow",
    "style": "magenta",
    "perf": "cyan",
    "test": "cyan",
    "build": "cyan",
    "ci": "cyan",
    "chore": "cyan",
    "revert": "cyan",
}

CONVENTIONAL_REGEX = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\./+]+\))?: .+$"

CONVENTIONAL_PATTERN = re.compile(
    r"^(?::\w+:|[\U00010000-\U0010ffff]\s*)?\s*"
    r"(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?!?\s*:\s*(?P<subject>.+)$"
)

# Empty tree hash for git (used when there's no parent commit)
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# Default prompt template
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

# Interactive review prompt choices
REVIEW_CHOICES = "[y]es, [n]o, [e]dit, [r]etry, re[f]ine, [s]elect"

# Max diff length for PR generation
PR_MAX_DIFF_LENGTH = 20000
