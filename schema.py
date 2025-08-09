'''
We will define our schema here for interacting with the LLM API.
'''

from pydantic import BaseModel

class ResponseBody(BaseModel):
    """
    Schema for structured communication between the agent and the LLM API.

    Attributes:
        action_description (str): Description of what the agent is doing and why.
        action (int): 0=file system, 1=shell, 2=agent response.
        response (str): Message output (for agent response).
        shell_command (str): Shell command to execute when action=1.
        file_action (int): 0=read, 1=write (when action=0).
        file_name (str): File path for reading/writing (when action=0).
        write_content (str): File content for writing (when file_action=1).
        finished (bool): Indicator for agent loop completion.
    """
    action_description: str
    action: int
    response: str
    shell_command: str
    file_action: int
    file_name: str
    write_content: str
    finished : bool=False

