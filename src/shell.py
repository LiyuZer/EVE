import subprocess
from src.logging_config import setup_logger

class ShellInterface:
    def __init__(self):
        self.logger = setup_logger(__name__)

    def execute_command(self, command: str):
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            stdout, stderr = result.stdout, result.stderr
            self.logger.info(f"Executed command: {command}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            return stdout, stderr
        except Exception as e:
            self.logger.error(f"Shell error for command '{command}': {e}")
            return '', f"SYSTEM_BLOCK: Shell error: {e}"
