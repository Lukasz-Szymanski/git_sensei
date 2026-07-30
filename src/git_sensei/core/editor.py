"""External editor integration for commit message editing."""
import os
import shlex
import subprocess
import sys
import tempfile
from typing import Optional


def get_editor() -> Optional[str]:
    """Get editor command using fallback chain.

    Priority: $VISUAL -> $EDITOR -> git config core.editor -> platform default
    """
    # Check environment variables
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
    if editor:
        return editor

    # Check git config
    try:
        result = subprocess.run(
            ['git', 'config', 'core.editor'],
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Platform defaults
    if sys.platform == 'win32':
        return 'notepad'
    else:
        return 'nano'


def edit_in_editor(message: str) -> Optional[str]:
    """Open message in external editor for editing.

    Returns edited message or None if editing failed/was cancelled.
    """
    editor = get_editor()
    if not editor:
        return None

    # Create temporary file with commit message
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        prefix='sensei_commit_',
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(message)
        f.write('\n\n# Edit your commit message above.')
        f.write('\n# Lines starting with # will be ignored.')
        temp_path = f.name

    try:
        # Build editor command
        if sys.platform == 'win32':
            # Windows: use shell=True for complex commands
            cmd = f'{editor} "{temp_path}"'
            subprocess.run(cmd, shell=True, check=True)
        else:
            # POSIX: split command properly
            cmd_parts = shlex.split(editor)
            cmd_parts.append(temp_path)
            subprocess.run(cmd_parts, check=True)

        # Read edited content
        with open(temp_path, 'r', encoding='utf-8') as f:
            edited = f.read()

        # Remove comment lines and strip
        lines = [line for line in edited.splitlines() if not line.startswith('#')]
        result = '\n'.join(lines).strip()

        return result if result else None

    except subprocess.CalledProcessError:
        return None
    except Exception:
        return None
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass
