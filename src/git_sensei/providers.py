import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Tuple


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.description = config.get("description", "")
        self.model = config.get("model")

    @abstractmethod
    def execute(self, diff: str, system_prompt: str) -> str:
        """Executes the provider request and returns the output."""

    @abstractmethod
    def check_health(self) -> bool:
        """Simple ping to check if provider is configured correctly."""

    def test_connection(self) -> Tuple[bool, str]:
        """Test real connection to AI provider."""
        if not self.check_health():
            return False, "Health check failed (missing config/executable)"

        test_prompt = "Reply with exactly one word: OK"
        try:
            result = self.execute("test", test_prompt)
            if result and "ok" in result.lower():
                return True, "Connection successful"
            elif result:
                return False, f"Unexpected response: {result[:100]}"
            else:
                return False, "No response from provider"
        except Exception as e:
            return False, str(e)


class CLIProvider(BaseProvider):
    """Provider that executes AI tasks via an external CLI tool."""
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.command_template = config.get("command")
        
    def execute(self, diff: str, system_prompt: str) -> str:
        if not self.command_template:
            raise ValueError(f"Provider '{self.name}' has no command defined.")

        try:
            args = shlex.split(self.command_template)
            args = [arg.replace("{system}", system_prompt) for arg in args]
        except ValueError as e:
            print(f"\n[Error] Invalid command template in config: {e}")
            return ""
            
        executable = shutil.which(args[0])
        if executable:
            args[0] = executable
        
        try:
            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Added timeout to prevent hanging on stalled CLI tools
            stdout, stderr = process.communicate(input=diff, timeout=45)

            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "Unknown error"
                print(f"\n[Provider Error] {self.name} failed (Exit Code {process.returncode})")
                print(f"Details: {error_msg}")
                return ""

            return stdout.strip()

        except subprocess.TimeoutExpired:
            process.kill()
            print(f"\n[Error] Command for '{self.name}' timed out after 45 seconds.")
            return ""
        except FileNotFoundError:
            print(f"\n[Error] Command not found for provider '{self.name}'.")
            if sys.platform != "win32":
                print(f"Command tried: {args[0]}")
            print("Please check your installation or PATH.")
            return ""
        except Exception as e:
            print(f"\n[Critical Error] {e}")
            return ""

    def check_health(self) -> bool:
        if not self.command_template:
            return False
        executable = shlex.split(self.command_template)[0]
        return shutil.which(executable) is not None


class GeminiProvider(BaseProvider):
    """Provider for the Google Gemini API."""
    def execute(self, diff: str, system_prompt: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("\n[Error] GEMINI_API_KEY environment variable not set.")
            print("Please set it using: export GEMINI_API_KEY='your_key'")
            return ""
            
        model = self.model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\nHere is the git diff:\n{diff}"
                        }
                    ]
                }
            ]
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            # Added a 15-second timeout for the HTTP request
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
                return ""
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                print("\n[API Error] Gemini API request timed out.")
            else:
                print(f"\n[API Error] Failed to connect to Gemini API: {e}")
            return ""
        except urllib.error.HTTPError as e:
            print(f"\n[API Error] Gemini API returned HTTP status {e.code}")
            try:
                print(f"Details: {e.read().decode('utf-8')}")
            except Exception:
                pass
            return ""
        except Exception as e:
            print(f"\n[API Error] Unexpected error communicating with Gemini API: {e}")
            return ""

    def check_health(self) -> bool:
        return os.getenv("GEMINI_API_KEY") is not None

    def test_connection(self) -> Tuple[bool, str]:
        if not self.check_health():
            return False, "Missing GEMINI_API_KEY environment variable"
        return super().test_connection()


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, DeepSeek, Local Ollama, etc.)."""
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.api_url = config.get("api_url")
        self.api_key_env = config.get("api_key_env")

    def execute(self, diff: str, system_prompt: str) -> str:
        url = self.api_url or "https://api.openai.com/v1/chat/completions"
        is_local = "localhost" in url or "127.0.0.1" in url
        env_key_name = self.api_key_env or "OPENAI_API_KEY"
        api_key = os.getenv(env_key_name)
        
        if not api_key and not is_local:
            print(f"\n[Error] {env_key_name} environment variable not set.")
            print(f"Please set it using: export {env_key_name}='your_key'")
            return ""
            
        key_val = api_key or "dummy"
        model = self.model or "gpt-4o-mini"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key_val}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze the diff and generate the commit message:\n\n{diff}"}
            ]
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            # Added a 20-second timeout for the HTTP request
            with urllib.request.urlopen(req, timeout=20) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return ""
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                print("\n[API Error] Custom/OpenAI API request timed out.")
            else:
                print(f"\n[API Error] Failed to connect to Custom/OpenAI API: {e}")
            return ""
        except urllib.error.HTTPError as e:
            print(f"\n[API Error] Custom/OpenAI API returned HTTP status {e.code}")
            try:
                print(f"Details: {e.read().decode('utf-8')}")
            except Exception:
                pass
            return ""
        except Exception as e:
            print(f"\n[API Error] Unexpected error communicating with Custom/OpenAI API: {e}")
            return ""

    def check_health(self) -> bool:
        url = self.api_url or "https://api.openai.com/v1/chat/completions"
        if "localhost" in url or "127.0.0.1" in url:
            return True
        env_key = self.api_key_env or "OPENAI_API_KEY"
        return os.getenv(env_key) is not None

    def test_connection(self) -> Tuple[bool, str]:
        if not self.check_health():
            env_key = self.api_key_env or "OPENAI_API_KEY"
            return False, f"Missing {env_key} environment variable"
        return super().test_connection()


def AIProvider(name: str, config: dict) -> BaseProvider:
    """
    Factory function that returns the appropriate provider strategy
    based on the configuration.
    """
    api_type = config.get("api_type")
    api_url = config.get("api_url")
    
    if api_type == "gemini":
        return GeminiProvider(name, config)
    elif api_type == "openai" or api_url:
        return OpenAIProvider(name, config)
    else:
        return CLIProvider(name, config)
