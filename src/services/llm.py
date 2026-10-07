"""LLM client service wrapper using OpenAI's client for Ollama/OpenAI-compatible APIs."""

import time
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from src.core.config import settings
from src.core.logging import logger


class LLMService:
    """Service wrapping LLM interactions via OpenAI compatible API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        logger.info(f"Initialized LLMService with model '{self.model}' at '{self.base_url}'")

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generate a completion response from the configured model."""
        start_time = time.perf_counter()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            temperature=temperature,
            **kwargs,
        )
        latency = time.perf_counter() - start_time
        choice = response.choices[0]
        content = choice.message.content or ""
        logger.debug(f"LLM call finished in {latency:.2f}s with {len(content)} chars.")
        return content

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Generate a JSON completion response enforcing structured JSON object."""
        return await self.generate_response(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            **kwargs,
        )


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Retrieve singleton LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
