# Auto-completion agent prompt
from src.prompt import completion_prompt
from src.prompt import completion_prompt_qwen
from src.llm import llmInterface
import src.schema as schema
import os
import json
from typing import Optional, Iterator


class AutoCompletionAgent:
    def __init__(self, completion_length: int = 50, model: str = "gpt-4.1-nano",
                 api_key: Optional[str] | None = None, llm: Optional[llmInterface] | None = None):
        """
        Initialize the auto-completion agent.
        generate_completion also accepts explicit prefix/suffix values.
        """
        self.completion_length = completion_length
        self.model = model
        # Resolve API key at runtime to avoid capturing None at import time
        resolved_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_TOKEN")
        self.llm = llm if llm is not None else llmInterface(api_key=resolved_key, model=model)

    def _max_output_tokens(self) -> int:
        """Approximate mapping from characters to tokens with a safety margin and clamp."""
        est = max(8, int(self.completion_length / 4) + 8)
        return min(est, 256)


    def generate_completion(self, prefix: str, suffix: str, language: Optional[str] = None, context: Optional[str] = None) -> str:
        """
        Generate the auto-completion based on the prefix and suffix.
        Returns the completion string.
        Optionally includes a language hint for better fidelity.
        """
        payload_qwen = {
            "role": "system",
            "content": str(
                {
                    "prefix": prefix,
                    "suffix": suffix,
                    "context": context or "",
                    "completion_length": self.completion_length
                }
            )
        }
        try:
            response = self.llm.generate_response_qwen(
                input_json=payload_qwen,
                completion_prompt=completion_prompt_qwen
            )
            return response
        except Exception as e:
            print(f"Error generating completion: {e}")
            raise e

