from pathlib import Path
from src.logging_config import setup_logger
import subprocess
import tempfile
from pathlib import Path

class FileHandler:
    def __init__(self):
        self.logger = setup_logger(__name__)

    def read_file(self, filename: str) -> str:
        try:
            with open(filename, 'r') as file:
                content = file.read()
            self.logger.info(f"Read from file: {filename}")
            return content
        except Exception as e:
            self.logger.error(f"Error reading file {filename}: {e}")
            return f"Error reading file: {e}"

    def write_file(self, filename: str, content: str) -> None:
        try:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, 'w') as file:
                file.write(content)
            self.logger.info(f"Wrote to file: {filename}")
        except Exception as e:
            self.logger.error(f"Error writing file {filename}: {e}")
            return f"Error writing file: {e}"


    def insert_diff(self, filename: str, diff: str) -> str:
        # Ensure file path is absolute
        file_path = Path(filename).resolve()

        # Write diff to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write(diff)
            tmp_path = tmp.name

        try:
            subprocess.run(
                ["patch", "-u", str(file_path), "-i", tmp_path],
                check=True,
                capture_output=True,
                text=True
            )
            return f"Applied diff to file: {filename}"
        except subprocess.CalledProcessError as e:
            return f"Failed to apply diff: {e.stderr or e.stdout}"
