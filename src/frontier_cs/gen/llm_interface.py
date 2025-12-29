import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import google.generativeai as genai
from anthropic import Anthropic, APITimeoutError as AnthropicAPITimeoutError
from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """
    Abstract base class for integrating Large Language Models (LLMs) into a competitive programming context.
    """

    def __init__(self):
        """
        Initialize the LLMInterface with a predefined prompt for generating competitive programming solutions.
        """
        self.prompt = """
        You are a competitive programmer. You will be given a problem statement, please implement a solution in C++. The execution time and memory limit are also stated in the statement so be aware of the complexity of the program. Please wrap the code in ```cpp and ``` so that it is properly formatted. Your response should ONLY contain the C++ code, with no additional explanation or text.
        """

    @abstractmethod
    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """
        Abstract method to interact with the LLM.
        """
        pass

    def generate_solution(self, problem_statement: str) -> Tuple[str, Any]:
        """
        Generates a solution to a given competitive programming problem using the LLM.
        """
        user_prompt = self.prompt + problem_statement
        response, meta = self.call_llm(user_prompt)
        return response, meta


class GPT(LLMInterface):
    """Concrete implementation of LLMInterface using OpenAI chat models."""

    def __init__(
        self,
        model: str = "gpt-5",
        reasoning_effort: Optional[str] = "high",
        timeout: float = 600.0,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__()
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        client_kwargs = {"api_key": resolved_key, "timeout": timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self.name = 'gpt'
        self.model = model
        self.reasoning_effort = reasoning_effort

    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """Sends the user prompt to the configured OpenAI model."""
        try:
            request_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            if self.reasoning_effort:
                request_kwargs["reasoning_effort"] = self.reasoning_effort
            completion = self.client.chat.completions.create(**request_kwargs)
            return completion.choices[0].message.content, str(completion)
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            return "", str(e)
        except Exception as e:
            logger.exception(f"OpenAI API error: {e}")
            return "", str(e)

class Gemini(LLMInterface):
    """
    Concrete implementation of LLMInterface using Google's Gemini 2.5 Pro model.

    Attributes:
        model (genai.GenerativeModel): Instance for interacting with the Gemini API.
    """

    def __init__(self, model: str = 'gemini-2.5-pro', timeout: float = 600.0, api_key: Optional[str] = None):
        """
        Initializes the GeminiLLM class by configuring the API key and creating an 
        instance of the Gemini model.
        """
        super().__init__()
        try:
            resolved_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not resolved_key:
                raise ValueError("GOOGLE_API_KEY not set")
            self.api_key = resolved_key
            genai.configure(api_key=self.api_key)
            # Using a powerful and recent model. You can change this to other available models.
            self.model_name = model
            self.timeout = timeout
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            self.model = None
        self.name = 'gemini'

    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """
        Sends the user prompt to the Gemini model and retrieves the solution.
        """
        if not self.model:
            return "Error: Model not initialized.", None

        try:
            if hasattr(self, "api_key") and self.api_key:
                genai.configure(api_key=self.api_key)
            response = self.model.generate_content(
                user_prompt,
                request_options={"timeout": self.timeout} 
            )
            solution_text = response.text
            return solution_text, response
        except Exception as e:
            logger.exception(f"Gemini API error: {e}")
            return f"Error: {e}", None


class ClaudeBase(LLMInterface):
    """Shared Anthropic client wrapper."""

    def __init__(
        self,
        model: str,
        name: str = 'claude',
        max_tokens: int = 32000,
        thinking_budget: Optional[int] = 20000,
        timeout: float = 600.0,
        api_key: Optional[str] = None,
    ):
        super().__init__()
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=resolved_key, timeout=timeout)
        self.name = name
        self.model = model
        self.max_tokens = max_tokens
        self.thinking_budget = thinking_budget

    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """Sends the combined user prompt to Anthropic's model."""
        try:
            request_kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            if self.thinking_budget:
                request_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                }

            completion = self.client.messages.create(**request_kwargs)

            final_text = ""
            if hasattr(completion, 'content') and completion.content:
                for block in completion.content:
                    if getattr(block, 'type', None) == 'text' and hasattr(block, 'text'):
                        final_text += block.text

            return final_text, str(completion)

        except AnthropicAPITimeoutError as e:
            logger.error(f"Anthropic API timeout: {e}")
            return "", str(e)
        except Exception as e:
            logger.exception(f"Anthropic API error: {e}")
            return "", str(e)


class Claude(ClaudeBase):
    def __init__(self, model: str = "claude-sonnet-4-20250514", **kwargs):
        super().__init__(model=model, **kwargs)


class Claude_Opus(ClaudeBase):
    def __init__(self, model: str = "claude-opus-4-1-20250805", **kwargs):
        super().__init__(model=model, **kwargs)


class Claude_Sonnet_4_5(ClaudeBase):
    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

class DeepSeek(LLMInterface):
    """
    Concrete implementation of LLMInterface using DeepSeek's models.

    For deepseek-reasoner (R1/V3.2), max_tokens controls total output
    including Chain-of-Thought reasoning. Default 32K, max 64K.
    """

    def __init__(
        self,
        model: str = "deepseek-reasoner",
        max_tokens: int = 32000,
        timeout: float = 600.0,
        base_url: str = "https://api.deepseek.com",
        api_key: Optional[str] = None,
    ):
        super().__init__()
        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.client = OpenAI(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout
        )
        self.name = 'deepseek'
        self.model = model
        self.max_tokens = max_tokens

    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """Sends the user prompt to DeepSeek's model."""
        try:
            request_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": self.max_tokens,
            }
            completion = self.client.chat.completions.create(**request_kwargs)
            return completion.choices[0].message.content, str(completion)
        except APITimeoutError as e:
            logger.error(f"DeepSeek API timeout: {e}")
            return "", str(e)
        except Exception as e:
            logger.exception(f"DeepSeek API error: {e}")
            return "", str(e)


class Grok(LLMInterface):
    """
    Concrete implementation of LLMInterface using xAI's Grok models.
    """

    def __init__(
        self,
        model: str = "grok-4",
        reasoning_effort: Optional[str] = "high",
        timeout: float = 600.0,
        base_url: str = "https://api.x.ai/v1",
        api_key: Optional[str] = None,
    ):
        """
        Initializes the Grok class by creating an instance of the OpenAI client
        pointed at the Grok API endpoint.
        """
        super().__init__()
        resolved_key = api_key or os.getenv("XAI_API_KEY")
        self.client = OpenAI(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout
        )
        self.name = 'grok'
        self.model = model
        self.reasoning_effort = reasoning_effort

    def call_llm(self, user_prompt: str) -> Tuple[str, Any]:
        """
        Sends the combined user prompt to Grok's model.

        Args:
            user_prompt (str): The complete prompt (system + problem).

        Returns:
            Tuple[str, Any]: The LLM's response and metadata.
        """
        try:
            # Reverted to the simpler, single-message format
            request_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            }
            if self.reasoning_effort:
                request_kwargs["reasoning_effort"] = self.reasoning_effort
            completion = self.client.chat.completions.create(**request_kwargs)
            return completion.choices[0].message.content, str(completion)
        except APITimeoutError as e:
            logger.error(f"Grok API timeout: {e}")
            return "", str(e)
        except Exception as e:
            logger.exception(f"Grok API error: {e}")
            return "", str(e)
