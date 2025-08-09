from pathlib import Path
from src.logging_config import setup_logger

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
            raise e
