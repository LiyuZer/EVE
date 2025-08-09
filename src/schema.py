# Example schema for ResponseBody (can expand as needed for project logic)

from pydantic import BaseModel
from typing import Optional

class ResponseBody(BaseModel):
    action_description: str
    shell_command: str
    file_action: int
    file_name: str
    write_content: str
    finished: bool = False
    response: Optional[str] = None
    action: int

# You can add additional pydantic models/types/functions here as needed.
# If you require 'base_prompt', import it using absolute import, e.g.,
# from src.prompt import base_prompt
