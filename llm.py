'''
We will interact with the LLM API to send and receive messages.
'''

from openai import OpenAI
from pydantic import BaseModel
from schema import *

class llmInterface:
    """
    Interface for communicating with the LLM (Large Language Model) API.
    """
    def __init__(self, api_key, model):
        """
        Initialize llmInterface with API key and model name.
        Args:
            api_key (str): API key for authentication.
            model (str): Model name to use with the API.
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_response(self, input_text, text_format):
        """
        Send a prompt to the LLM and receive the structured parsed response.
        Args:
            input_text (str): Prompt to provide as context for the LLM.
            text_format (type): Pydantic model for response parsing.
        Returns:
            Parsed output according to the given text_format.
        """
        resp = self.client.responses.parse(
            model=self.model,
            input=input_text,
            text_format=text_format
        )
        return resp.output_parsed
