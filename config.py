import os
import sys
from typing import Dict, Any

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
        """Loads config from ~/.sensei.toml or local .sensei.toml"""
        paths = [
            os.path.expanduser("~/.sensei.toml"),
            os.path.join(os.getcwd(), ".sensei.toml"),
            os.path.join(os.path.dirname(__file__), ".sensei.toml") # Default inside package
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
