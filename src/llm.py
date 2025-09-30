from typing import Any, List, Dict, Optional
import os
import json
import requests
from openai import OpenAI
import anthropic
from src.logging_config import setup_logger


class CompletionError(Exception):
    pass


class llmInterface:
    def __init__(self, api_key: str | None, model: str, org : str = "OpenAI"):
        self.logger = setup_logger(__name__)
        self.model = model
        self.org = org

        # OpenAI client is optional for autocomplete; initialize lazily
        resolved_openai = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_TOKEN")
        self.api_key = resolved_openai

        # TODO: Make this cleaner with a factory pattern
        if self.org.lower() == "openai":
            self.client: Optional[OpenAI] = None
            if self.api_key:
                try:
                    self.client = OpenAI(api_key=self.api_key)
                except Exception:
                    # Don't fail constructor; generate_response will try again or raise clearly
                    self.client = None
        elif self.org.lower() == "anthropic":
            self.client = anthropic.Anthropic(api_key=self.api_key)

        # Fireworks API key (used by autocomplete path)
        self.fireworks_key = os.getenv("FIREWORKS_API_KEY")
        self.fireworks_model = os.getenv(
            "FIREWORKS_MODEL",
            "accounts/fireworks/models/qwen3-coder-480b-a35b-instruct",
        )

    def generate_response_qwen(self, input_json: Dict[str, Any], completion_prompt: Dict[str, Any]) -> str:
        """
        Call Fireworks chat completions for Qwen coder model.
        Returns the raw completion string (as specified by server agent).
        """
        if not self.fireworks_key:
            raise CompletionError("Missing FIREWORKS_API_KEY for autocomplete")

        url = "https://api.fireworks.ai/inference/v1/chat/completions"
        payload = {
            "model": self.fireworks_model,
            "top_p": 0.95,
            "top_k": 60,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "temperature": 0.9,
            "messages": [
                completion_prompt,
                input_json,
            ],
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.fireworks_key}",
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=3)
            r.raise_for_status()
            j = r.json()
            content = j["choices"][0]["message"]["content"]
            # The completion is expected to be a JSON string with a "completion" field
            return json.loads(content)["completion"]
        except requests.Timeout as e:
            raise CompletionError("Fireworks request timed out") from e
        except Exception as e:
            # Include body if available for easier debugging
            body = None
            try:
                body = r.text  # type: ignore[name-defined]
            except Exception:
                pass
            raise CompletionError(f"Failed to generate response via Fireworks: {e} - {body}") from e

    def generate_response(self, input_text: str, text_format=None, images = [], **kwargs: Any):
        if self.org.lower() == "openai":
            return self.generate_response_openai(input_text, text_format=text_format, images = images, **kwargs)
        elif self.org.lower() == "anthropic":
            response = self.generate_response_anthropic(input_text, **kwargs)
            # Convert to structured text format a pydantic schema 
            return text_format.model_validate_json(response)
    def generate_response_openai(self, input_text: str, text_format=None, images = [], **kwargs: Any):
        """
        Call OpenAI Responses.parse for structured output (non-autocomplete paths).
        Lazily initialize the OpenAI client only when needed.
        """
        # Lazy init if needed
        if self.client is None:
            resolved = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_TOKEN")
            if not resolved:
                msg = (
                    "Missing OpenAI API key. Set OPENAI_API_KEY in your environment or create a .env file with\n"
                    "OPENAI_API_KEY=your_key_here (restart the IDE after setting)."
                )
                self.logger.error(msg)
                raise ValueError(msg)
            try:
                self.client = OpenAI(api_key=resolved)
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise

        try:
            if kwargs:
                self.logger.debug(f"responses.parse extra kwargs: {kwargs}")
            resp = self.client.responses.parse(  # type: ignore[union-attr]
                model=self.model,
                input= [{
                        "role": "user",
                        "content" : [
                            {
                                "type" : "input_text",
                                "text": input_text
                            },
			*[{"type" : "input_text", "text" : img["file_path"]} for img in images], 

                            *[{"type": "input_image", "image_url": "data:image/png;base64," + img["img_str"]} for img in images]
                        ]
                    }
                ],
                text_format=text_format,
            )
            self.logger.info("LLM responded successfully")
            return resp.output_parsed
        except Exception as e:
            self.logger.error(f"LLM API error: {e}")
            raise e
    def generate_response_anthropic(self, input_text: str, **kwargs: Any):
        """
        Anthropic uses messages.create
        """
        if self.client is None:
            raise ValueError("Missing Anthropic API key for completions")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10000,
                messages=[
                    {"role": "user", "content": input_text}
                ],
                **kwargs
            )
            self.logger.info("Anthropic LLM responded successfully")
            output = response.content[0].text
            left_brace = output.find("{")
            right_brace = output.rfind("}")
            if left_brace != -1 and right_brace != -1 and right_brace > left_brace:
                output = output[left_brace:right_brace + 1]
                return output
            else:
                raise ValueError("Could not find JSON object in the response")
        except Exception as e:
            self.logger.error(f"Anthropic LLM API error: {e}")
            raise e
    def generate_embedding(self, text: str) -> list[float]:
        # Lazy init for embeddings as well
        if self.client is None:
            resolved = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_TOKEN")
            if not resolved:
                raise ValueError("Missing OpenAI API key for embeddings")
            self.client = OpenAI(api_key=resolved)
        try:
            embedding = self.client.embeddings.create(  # type: ignore[union-attr]
                model="text-embedding-3-large",
                input=text,
            )
            return embedding.data[0].embedding
        except Exception as e:
            self.logger.error(f"LLM API error while generating embedding: {e}")
            raise e