# Example schema for ResponseBody (can expand as needed for project logic)

from pydantic import BaseModel
from typing import Optional

class Diff(BaseModel):
    line_range_1: list[int]
    line_range_2: list[int]
    file_path: str = ""  # Allow empty default so tests can omit this field
    Add: bool
    Remove: bool
    Replace: bool
    content: str

class ResponseBody(BaseModel):
    action: int
    action_description: str
    shell_command: str = ""
    file_action: int = 0
    file_name: str = ""
    write_content: str = ""
    finished: bool = False
    response: Optional[str] = None
    diff: Optional[Diff] = None  # Make this optional!
    node_hash: str = ""
    node_content: str = ""
    save_content: str = ""
    retrieve_content: str = ""
    # New: optional short label for the context node (threads into metadata["label"]; used by tree labels)
    node_label: Optional[str] = ""

class AutoCompletionResponse(BaseModel):
    completion: str

class SmartTerminalResponse(BaseModel):
    command: str