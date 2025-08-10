# Example schema for ResponseBody (can expand as needed for project logic)

from pydantic import BaseModel
from typing import Optional

class Diff(BaseModel):
    line_range_1: list[int]
    line_range_2: list[int]
    Add: bool
    Remove: bool
    Replace: bool
    content: str

class ResponseBody(BaseModel):
    action: int
    action_description: str
    shell_command: str
    file_action: int
    file_name: str
    write_content: str
    finished: bool = False
    response: Optional[str] = None
    diff: Diff
    node_hash: str
    node_content: str
    save_content: str
    retrieve_content: str
 