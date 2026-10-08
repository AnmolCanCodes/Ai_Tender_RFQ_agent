from huggingface_hub import InferenceClient

from app.core.config import settings


class LLMClient:
    """Wrapper for Hugging Face Inference API with unified generate interface."""

    def __init__(self):
        self.client = InferenceClient(
            api_key=settings.HF_TOKEN
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generates text response using the configured LLM model."""
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        response = self.client.chat.completions.create(
            model=settings.HF_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Returns singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
