import os
import subprocess
from typing import Optional
from src.logging_config import setup_logger

class ShellInterface:
    def __init__(self, timeout_seconds: Optional[int] = None, max_capture: Optional[int] = None):
        self.logger = setup_logger(__name__)
        try:
            self.timeout_seconds = int(timeout_seconds if timeout_seconds is not None else os.getenv("EVE_SHELL_TIMEOUT", "1000"))
        except Exception:
            self.timeout_seconds = 1000
        try:
            self.max_capture = int(max_capture if max_capture is not None else os.getenv("EVE_SHELL_MAX_CAPTURE", "50000"))
        except Exception:
            self.max_capture = 50000

    def _truncate(self, s: str) -> str:
        if s is None:
            return ''
        if len(s) <= self.max_capture:
            return s
        extra = len(s) - self.max_capture
        return s[: self.max_capture] + f"\n[...truncated {extra} chars]"

    def execute_command(self, command: str):
        try:
            # Honor IDE-selected workspace if provided
            cwd = os.getenv("EVE_WORKSPACE_ROOT")
            if cwd and not os.path.isdir(cwd):
                cwd = None
            result = subprocess.run(
                command,
                shell=True,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                cwd=cwd,
            )
            stdout, stderr = result.stdout, result.stderr
            stdout = self._truncate(stdout)
            stderr = self._truncate(stderr)
            self.logger.info(f"Executed command: {command}\nCWD: {cwd or '[process default]'}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            return stdout, stderr
        except subprocess.TimeoutExpired:
            msg = f"SYSTEM_BLOCK: Command timed out after {self.timeout_seconds}s"
            self.logger.warning(f"{msg}: {command}")
            return "", msg
        except Exception as e:
            self.logger.error(f"Shell error for command '{command}': {e}")
            return '', f"SYSTEM_BLOCK: Shell error: {e}"