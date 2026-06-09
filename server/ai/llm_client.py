from core.logger import logger
"""
Ayura AI - Dual-Provider LLM Client
Uses Azure OpenAI first and falls back to Google Gemini automatically.
"""

import asyncio
import time

from config import settings
from core.metrics import metrics_registry


class LLMClient:
    """Abstraction layer over Azure OpenAI and Google Gemini."""

    def __init__(self):
        self._azure_client = None
        self._gemini_model = None
        self._available_provider = "none"
        self._last_used_provider = "none"
        self._initialize()

    def _initialize(self):
        """Initialize available LLM providers."""
        # Initialize Azure OpenAI (Primary)
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            try:
                from openai import AsyncAzureOpenAI

                self._azure_client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    timeout=60.0,
                )
                self._available_provider = "azure_openai"
                logger.info("  [OK] Azure OpenAI client initialized")
            except Exception as exc:
                logger.warning(f" Azure OpenAI init failed: {exc}")

        # Initialize Gemini (Fallback)
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
                if self._available_provider == "none":
                    self._available_provider = "gemini"
                logger.info("  [OK] Google Gemini client initialized")
            except Exception as exc:
                logger.warning(f" Gemini init failed: {exc}")

        if self._available_provider == "none":
            logger.warning(" No LLM provider available. Set AZURE_OPENAI_API_KEY or GEMINI_API_KEY.")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Generate text with Azure-first strategy and Gemini fallback."""
        self._last_used_provider = "none"
        started = time.perf_counter()
        prompt_chars = len(prompt) + len(system_prompt)

        # 1) Try Azure OpenAI first
        if self._azure_client:
            try:
                response = await self._generate_azure(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                self._last_used_provider = "azure_openai"
                self._record_call(started, "azure_openai", True, prompt_chars, len(response), json_mode)
                return response
            except Exception as exc:
                self._record_call(started, "azure_openai", False, prompt_chars, 0, json_mode)
                logger.warning(f" Azure OpenAI call failed: {exc}. Falling back to Gemini.")

        # 2) Fallback to Gemini
        if self._gemini_model:
            try:
                response = await self._generate_gemini(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                self._last_used_provider = "gemini"
                self._record_call(started, "gemini", True, prompt_chars, len(response), json_mode)
                return response
            except Exception as exc:
                self._record_call(started, "gemini", False, prompt_chars, 0, json_mode)
                logger.error(f" Gemini call failed: {exc}")

        self._last_used_provider = "none"
        response = '{"error":"No LLM provider available. Configure AZURE_OPENAI_API_KEY or GEMINI_API_KEY."}'
        self._record_call(started, "none", False, prompt_chars, len(response), json_mode)
        return response

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Yield generated text chunks as an asynchronous generator."""
        self._last_used_provider = "none"
        
        # 1) Try Azure OpenAI first
        if self._azure_client:
            try:
                self._last_used_provider = "azure_openai"
                async for chunk in self._generate_azure_stream(prompt, system_prompt, temperature, max_tokens):
                    yield chunk
                return
            except Exception as exc:
                logger.warning(f" Azure OpenAI stream failed: {exc}. Falling back to Gemini.")

        # 2) Fallback to Gemini
        if self._gemini_model:
            try:
                self._last_used_provider = "gemini"
                async for chunk in self._generate_gemini_stream(prompt, system_prompt, temperature, max_tokens):
                    yield chunk
                return
            except Exception as exc:
                logger.error(f" Gemini stream failed: {exc}")

        yield "Error: No LLM provider available for streaming."

    async def _generate_azure(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Generate using Azure OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": settings.AZURE_OPENAI_DEPLOYMENT,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._azure_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Azure returned empty response content.")
        return content

    async def _generate_gemini(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Generate using Google Gemini."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        # Ask Gemini for strict JSON output when needed.
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        response = await asyncio.wait_for(
            self._gemini_model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            ),
            timeout=60.0,
        )

        text = getattr(response, "text", None)
        if text:
            return text

        # Some Gemini responses may not populate response.text directly.
        candidates = getattr(response, "candidates", None) or []
        if candidates and getattr(candidates[0], "content", None):
            parts = getattr(candidates[0].content, "parts", None) or []
            extracted = "".join(getattr(part, "text", "") for part in parts if getattr(part, "text", None))
            if extracted:
                return extracted

        raise RuntimeError("Gemini returned empty response content.")

    async def _generate_azure_stream(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self._azure_client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=True
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _generate_gemini_stream(self, prompt: str, system_prompt: str, temperature: float, max_tokens: int):
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        generation_config = {"temperature": temperature, "max_output_tokens": max_tokens}
        
        response = await self._gemini_model.generate_content_async(
            full_prompt,
            generation_config=generation_config,
            stream=True
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    @property
    def provider(self) -> str:
        """Provider used by the most recent successful generation."""
        if self._last_used_provider != "none":
            return self._last_used_provider
        return self._available_provider

    @staticmethod
    def _record_call(
        started: float,
        provider: str,
        success: bool,
        prompt_chars: int,
        response_chars: int,
        json_mode: bool,
    ) -> None:
        latency_ms = round((time.perf_counter() - started) * 1000)
        metrics_registry.record_llm_call(
            provider=provider,
            latency_ms=latency_ms,
            success=success,
            prompt_chars=prompt_chars,
            response_chars=response_chars,
            json_mode=json_mode,
        )


# Singleton instance
llm_client = LLMClient()
