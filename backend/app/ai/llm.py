"""
Hugging Face LLM client with resilience, exponential backoff,
timeout controls, and strict token/payload sanitization.
"""

import logging
import time
from typing import Any, Sequence
import httpx
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError

from app.core.config import settings
from app.utils.helper import sanitize_prompt_input

logger = logging.getLogger("app.ai.llm")

DEFAULT_TIMEOUT_SECONDS = 45.0
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2.0


class HuggingFaceLLMClient:
    """
    Robust client for querying Hugging Face Inference API.
    Enforces timeouts, error recovery, exponential backoff, and tenant sanitization.
    """

    def __init__(
        self,
        model: str | None = None,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.model = model or settings.HF_MODEL
        self.token = token or settings.HF_TOKEN
        self.timeout = timeout
        self._client: InferenceClient | None = None

    @property
    def client(self) -> InferenceClient:
        if self._client is None:
            self._client = InferenceClient(
                model=self.model,
                token=self.token,
                timeout=self.timeout,
            )
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generates text via chat completion or fallback text generation with retries.

        Args:
            prompt: User message / instruction.
            system_prompt: Optional system boundary directive.
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Max new tokens to prevent resource runaway.

        Returns:
            Generated response string.
        """
        clean_user_prompt = sanitize_prompt_input(prompt)
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": sanitize_prompt_input(system_prompt)})
        messages.append({"role": "user", "content": clean_user_prompt})

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # First try chat_completion
                response = self.client.chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        return content.strip()
                return ""

            except (HfHubHTTPError, httpx.HTTPError, Exception) as exc:
                last_error = exc
                error_msg = str(exc)
                logger.warning(
                    "LLM query attempt %d/%d failed on model %s: %s",
                    attempt,
                    MAX_RETRIES,
                    self.model,
                    error_msg[:150],
                )

                # Check if it's a rate limit or model loading status (503 / 429)
                if attempt < MAX_RETRIES:
                    sleep_time = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    time.sleep(sleep_time)

        # Fallback: if chat_completion failed across retries, try direct text_generation
        try:
            full_prompt = f"{system_prompt}\n\n{clean_user_prompt}" if system_prompt else clean_user_prompt
            text_resp = self.client.text_generation(
                prompt=full_prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
            )
            if isinstance(text_resp, str) and text_resp.strip():
                return text_resp.strip()
        except Exception as fallback_exc:
            logger.error("LLM fallback text_generation failed: %s", str(fallback_exc)[:150])

        raise RuntimeError(
            f"Failed to generate completion from Hugging Face model after {MAX_RETRIES} attempts. Cause: {last_error}"
        )


# Singleton instance initialized with environment configuration
llm_client = HuggingFaceLLMClient()


def get_llm_client() -> HuggingFaceLLMClient:
    """Dependency provider for Hugging Face LLM client."""
    return llm_client
