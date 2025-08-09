'''
Our file system, we will define a file handler, we will use this handler to interact with the file system, allowing us to read and write files as needed.
'''

from typing import Optional

class FileHandler:
    """
    Handles reading from and writing to the local file system.
    """
    def __init__(self) -> None:
        """
        Initialize FileHandler instance.
        """
        pass

    def read_file(self, file_path: str) -> str:
        """
        Read the contents of a file.
        Args:
            file_path (str): Path to the file to be read.
        Returns:
            str: Contents of the file, or error string if exception occurs.
        """
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            return str(e)

    def write_file(self, file_path: str, content: str) -> Optional[str]:
        """
        Write content to a file, overwriting if it exists.
        Args:
            file_path (str): Path to the file to be written.
            content (str): Data to write to the file.
        Returns:
            None if write is successful, or error string if exception occurs.
        """
        try:
            with open(file_path, 'w') as file:
                file.write(content)
            return None
        except Exception as e:
            return str(e)