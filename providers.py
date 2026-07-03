import subprocess
import shlex
import sys
import os
import json
import urllib.request
import urllib.error
import shutil
from typing import Optional

class AIProvider:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.command_template = config.get("command")
        self.description = config.get("description", "")
        self.api_type = config.get("api_type")
        self.model = config.get("model")
        self.api_url = config.get("api_url")
        self.api_key_env = config.get("api_key_env")

    def execute(self, diff: str, system_prompt: str) -> str:
        """
        Executes the provider CLI command or calls the native API.
        """
        if self.api_type == "gemini":
            return self._execute_gemini_api(diff, system_prompt)
        elif self.api_type == "openai" or self.api_url:
            return self._execute_openai_api(diff, system_prompt)

        if not self.command_template:
            raise ValueError(f"Provider '{self.name}' has no command or api_type defined.")

        # 1. Prepare Command
        escaped_prompt = system_prompt.replace('"', '\\"')
        final_cmd_str = self.command_template.replace("{system}", escaped_prompt)
        
        # 2. Execute
        try:
            if sys.platform == "win32":
                process = subprocess.Popen(
                    final_cmd_str,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
            else:
                args = shlex.split(final_cmd_str)
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
            
            stdout, stderr = process.communicate(input=diff)

            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "Unknown error"
                print(f"\n[Provider Error] {self.name} failed (Exit Code {process.returncode})")
                print(f"Details: {error_msg}")
                return ""

            return stdout.strip()

        except FileNotFoundError:
            print(f"\n[Error] Command not found for provider '{self.name}'.")
            if sys.platform != "win32":
                print(f"Command tried: {args[0]}")
            print("Please check your installation or PATH.")
            return ""
        except Exception as e:
            print(f"\n[Critical Error] {e}")
            return ""

    def _execute_gemini_api(self, diff: str, system_prompt: str) -> str:
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
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
                return ""
        except urllib.error.HTTPError as e:
            print(f"\n[API Error] Gemini API returned HTTP status {e.code}")
            try:
                print(f"Details: {e.read().decode('utf-8')}")
            except Exception:
                pass
            return ""
        except Exception as e:
            print(f"\n[API Error] Failed to connect to Gemini API: {e}")
            return ""

    def _execute_openai_api(self, diff: str, system_prompt: str) -> str:
        env_key_name = self.api_key_env or "OPENAI_API_KEY"
        api_key = os.getenv(env_key_name)
        if not api_key:
            print(f"\n[Error] {env_key_name} environment variable not set.")
            print(f"Please set it using: export {env_key_name}='your_key'")
            return ""
            
        model = self.model or "gpt-4o-mini"
        url = self.api_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
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
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return ""
        except urllib.error.HTTPError as e:
            print(f"\n[API Error] Custom/OpenAI API returned HTTP status {e.code}")
            try:
                print(f"Details: {e.read().decode('utf-8')}")
            except Exception:
                pass
            return ""
        except Exception as e:
            print(f"\n[API Error] Failed to connect to Custom/OpenAI API: {e}")
            return ""

    def check_health(self) -> bool:
        """
        Simple 'ping' to see if the command exists or environment variable is set.
        """
        if self.api_type == "gemini":
            return os.getenv("GEMINI_API_KEY") is not None
        elif self.api_type == "openai" or self.api_url:
            env_key = self.api_key_env or "OPENAI_API_KEY"
            return os.getenv(env_key) is not None

        if not self.command_template:
            return False

        executable = shlex.split(self.command_template)[0]
        return shutil.which(executable) is not None

    def test_connection(self) -> tuple:
        """Test real connection to AI provider.

        Returns:
             tuple: (success: bool, message: str)
        """
        if self.api_type == "gemini" or self.api_type == "openai" or self.api_url:
            if not self.check_health():
                key_name = "GEMINI_API_KEY" if self.api_type == "gemini" else (self.api_key_env or "OPENAI_API_KEY")
                return False, f"Missing {key_name} environment variable"
        else:
            if not self.check_health():
                return False, f"Command not found in PATH"

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
