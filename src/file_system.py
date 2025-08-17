from pathlib import Path
from src.logging_config import setup_logger
from collections import OrderedDict
from src.schema import Diff

class FileHandler:
    def __init__(self, base_root=None):
        self.logger = setup_logger(__name__)
        try:
            self.base_root = Path(base_root).resolve() if base_root else None
        except Exception:
            self.base_root = None
        if self.base_root:
            self.logger.info(f"FileHandler base_root set to: {self.base_root}")

    def _resolve(self, filename):
        try:
            p = Path(filename)
        except Exception:
            return Path(str(filename))
        if not p.is_absolute() and self.base_root:
            try:
                return (self.base_root / p).resolve()
            except Exception:
                return self.base_root / p
        return p

    def read_file(self, filename: str) -> dict:
        p = self._resolve(filename)
        print(f"Reading file: {p}")
        try:
            with open(p, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            line_dict = OrderedDict()
            for i, line in enumerate(lines, 1):
                line_dict[i] = line.rstrip()

            self.logger.info(f"Read file as line dict: {p}")
            return line_dict
        except Exception as e:
            self.logger.error(f"Error reading file {p}: {e}")
            return {"error": f"Error reading file: {e}"}

    def read_as_str(self, filename: str) -> str:
        p = self._resolve(filename)
        try:
            with open(p, 'r', encoding='utf-8') as file:
                content = file.read()
            self.logger.info(f"Read file as string: {p}")
            return content
        except Exception as e:
            self.logger.error(f"Error reading file {p}: {e}")
            return f"Error reading file: {e}"

    def write_file(self, filename: str, content: str) -> None:
        p = self._resolve(filename)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as file:
                file.write(content)
            self.logger.info(f"Wrote to file: {p}")
        except Exception as e:
            self.logger.error(f"Error writing file {p}: {e}")
            return f"Error writing file: {e}"

    def insert_diff(self, diff: Diff) -> str:
        try:
            file_path = self._resolve(diff.file_path)
            print(f"Applying diff to file: {file_path} with diff: {diff}")
            content = self.read_as_str(str(file_path))
            if content.startswith("Error reading file:"):
                return f"Error reading file for diff: {content}"

            lines = content.splitlines()
            total_lines = len(lines)

            # Validate line ranges
            start_line = max(0, diff.line_range_1[0] - 1)  # Convert to 0-based, ensure >= 0
            end_line = min(total_lines - 1, diff.line_range_1[1] - 1)  # Ensure <= max line

            # Additional validation
            if start_line > total_lines:
                return f"Error: Start line {diff.line_range_1[0]} exceeds file length ({total_lines} lines)"

            if diff.Add:
                # Insert new lines at specified position
                new_lines = diff.content.splitlines() if hasattr(diff, 'content') and diff.content else []
                lines[start_line:start_line] = new_lines

            elif diff.Remove:
                # Remove lines in the specified range
                if start_line <= end_line:  # Only remove if valid range
                    del lines[start_line:end_line + 1]

            elif diff.Replace:
                # Replace lines in range with new content
                new_lines = diff.content.splitlines() if hasattr(diff, 'content') and diff.content else []
                if start_line <= end_line:  # Only replace if valid range
                    lines[start_line:end_line + 1] = new_lines
                print(f"Replacing lines {start_line + 1} to {end_line + 1} with new content: {new_lines}")
            new_content = '\n'.join(lines)
            result = self.write_file(str(file_path), new_content)

            # Check if write_file returned an error
            if result and isinstance(result, str) and result.startswith("Error writing file:"):
                return result

            self.logger.info(f"Applied diff to file: {file_path}")
            return f"Applied diff to file: {file_path}"

        except Exception as e:
            # file_path may not be defined if resolution fails, so be careful in logging
            try:
                path_str = str(file_path)
            except Exception:
                path_str = str(getattr(diff, 'file_path', '<?>'))
            self.logger.error(f"Error applying diff to {path_str}: {e}")
            return f"Error applying diff: {e}"