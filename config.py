import os
import sys
import re
from typing import Dict, Any, Optional

# Try to import tomli (Python 3.11+ has tomllib built-in, otherwise generic tomli)
try:
    import tomllib as toml  # Python 3.11+
except ImportError:
    try:
        import tomli as toml  # External lib
    except ImportError:
        toml = None

DEFAULT_CONFIG = {
    "core": {
        "default_provider": "gemini"
    },
    "prompts": {
        "universal": """You are a professional git commit message generator.

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
    },
    "providers": {
        "gemini": {
            "description": "Google Gemini CLI",
            "command": "gemini --system \"{system}\""
        },
        "echo": {
            "description": "Debug (Echo)",
            "command": "cat"
        }
    }
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.load_config()

    def load_config(self):
        """Loads config from multiple sources. Later entries override earlier ones."""
        # Order: defaults -> package -> project -> user (highest priority)
        paths = [
            os.path.join(os.path.dirname(__file__), ".sensei.toml"),  # Package defaults
            os.path.join(os.getcwd(), ".sensei.toml"),                 # Project-level
            os.path.expanduser("~/.sensei.toml"),                      # User config (highest priority)
        ]

        if not toml:
            # Fallback if no TOML parser installed
            # We don't warn here to avoid spamming stdout, but we stick to defaults
            return

        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        data = toml.load(f)
                        self._merge_config(data)
                except Exception as e:
                    print(f"Warning: Failed to parse {path}: {e}")

    def _merge_config(self, new_data: Dict[str, Any]):
        """Deep merge for simple dicts"""
        for section, content in new_data.items():
            if section not in self.config:
                self.config[section] = content
            elif isinstance(content, dict):
                self.config[section].update(content)

    def get_provider_config(self, provider_name: str) -> Dict[str, str]:
        providers = self.config.get("providers", {})
        return providers.get(provider_name, None)

    def get_default_provider(self) -> str:
        return self.config.get("core", {}).get("default_provider", "gemini")

    def list_providers(self) -> Dict[str, str]:
        return {
            name: data.get("description", "")
            for name, data in self.config.get("providers", {}).items()
        }

    def get_universal_prompt(self) -> str:
        """Get the universal prompt template."""
        return self.config.get("prompts", {}).get("universal", "")

    def get_config_path(self) -> str:
        """Returns the path to user's config file (creates if needed)."""
        return os.path.expanduser("~/.sensei.toml")

    def set_default_provider(self, provider_name: str) -> bool:
        """Sets the default provider in the user's config file."""
        if provider_name not in self.config.get("providers", {}):
            return False

        config_path = self.get_config_path()

        # Read existing content or create new
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Update existing default_provider line
            if re.search(r'^default_provider\s*=', content, re.MULTILINE):
                content = re.sub(
                    r'^default_provider\s*=\s*["\']?\w+["\']?',
                    f'default_provider = "{provider_name}"',
                    content,
                    flags=re.MULTILINE
                )
            elif "[core]" in content:
                # Add under [core] section
                content = re.sub(
                    r'(\[core\])',
                    f'[core]\ndefault_provider = "{provider_name}"',
                    content
                )
            else:
                # Prepend [core] section
                content = f'[core]\ndefault_provider = "{provider_name}"\n\n' + content
        else:
            # Create new config file
            content = f'[core]\ndefault_provider = "{provider_name}"\n'

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update in-memory config
        self.config["core"]["default_provider"] = provider_name
        return True
