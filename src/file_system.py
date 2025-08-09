from pathlib import Path
from src.logging_config import setup_logger
import subprocess
import tempfile
import difflib
from pathlib import Path
from schema import Diff
from collections import OrderedDict

class FileHandler:
    def __init__(self):
        self.logger = setup_logger(__name__)

    def read_file(self, filename: str) -> dict:
        try:
            with open(filename, 'r') as file:
                lines = file.readlines()

            line_dict = OrderedDict()
            for i, line in enumerate(lines, 1):
                line_dict[i] = line.rstrip()
                        
            self.logger.info(f"Read file as line dict: {filename}")
            return line_dict
        except Exception as e:
            self.logger.error(f"Error reading file {filename}: {e}")
            return {"error": f"Error reading file: {e}"}

    def read_as_str(self, filename: str) -> str:
        try:
            with open(filename, 'r') as file:
                content = file.read()
            self.logger.info(f"Read file as string: {filename}")
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
            
    def insert_diff(self, filename: str, diff: Diff) -> str:
        try:
            print(f"Applying diff to file: {filename} with diff: {diff}")
            content = self.read_as_str(filename)
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
                        
            new_content = '\n'.join(lines)
            result = self.write_file(filename, new_content)
            
            # Check if write_file returned an error
            if result and result.startswith("Error writing file:"):
                return result
                
            self.logger.info(f"Applied diff to file: {filename}")
            return f"Applied diff to file: {filename}"
                    
        except Exception as e:
            self.logger.error(f"Error applying diff to {filename}: {e}")
            return f"Error applying diff: {e}"