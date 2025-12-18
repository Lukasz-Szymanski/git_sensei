import subprocess
import shlex
import sys
from typing import Optional

class AIProvider:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.command_template = config.get("command")
        self.description = config.get("description", "")

    def execute(self, diff: str, system_prompt: str) -> str:
        """
        Executes the provider CLI command.
        Replaces {system} in the command template with the actual prompt.
        Pipes 'diff' to stdin.
        """
        if not self.command_template:
            raise ValueError(f"Provider '{self.name}' has no command defined.")

        # 1. Prepare Command
        # We escape the system prompt to avoid shell injection issues when formatting
        # Ideally, complex prompts should be passed differently, but for CLI wrappers this is standard.
        # Note: simplistic replacement. 
        final_cmd_str = self.command_template.replace("{system}", system_prompt)
        
        # 2. Execute
        try:
            if sys.platform == "win32":
                # On Windows, using shell=True allows the system to resolve .cmd/.bat files automatically
                # and handles built-in commands better. We pass the full string, not a list.
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
                # On POSIX, we split args and avoid shell=True for slightly better security/performance
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
                # Basic error handling
                error_msg = stderr.strip() if stderr else "Unknown error"
                print(f"\n[Provider Error] {self.name} failed (Exit Code {process.returncode})")
                print(f"Details: {error_msg}")
                return ""

            return stdout.strip()

        except FileNotFoundError:
            print(f"\n[Error] Command not found for provider '{self.name}'.")
            print(f"Command tried: {args[0]}")
            print("Please check your installation or PATH.")
            return ""
        except Exception as e:
            print(f"\n[Critical Error] {e}")
            return ""

    def check_health(self) -> bool:
        """
        Simple 'ping' to see if the command exists and runs.
        We run it with --help or --version usually, but since the command is templated,
        we might just try to run the executable part.
        """
        if not self.command_template:
            return False
            
        # Extract just the executable (first word)
        executable = shlex.split(self.command_template)[0]
        
        # Using shutil.which is safer than running it
        import shutil
        return shutil.which(executable) is not None
