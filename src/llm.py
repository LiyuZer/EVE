from openai import OpenAI
import os
from src.logging_config import setup_logger

class llmInterface:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.logger = setup_logger(__name__)
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, input_text: str, text_format=None):
        try:
            resp = self.client.responses.parse(
                    model=self.model,
                    input=input_text,
                    text_format=text_format
                )

            self.logger.info("LLM responded successfully")
            return resp.output_parsed
        except Exception as e:
            self.logger.error(f"LLM API error: {e}")
            raise e
