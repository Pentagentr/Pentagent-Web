"""
Unified LLM wrapper to abstract provider differences.

Supports:
- Groq (default): Llama 3.3/3.1, Mixtral, GPT-OSS-120B (if available)
- HuggingFace Inference API (optional)

Provides a Gemini-compatible method: generate_content_async(prompt)
so existing call sites can stay unchanged.
"""

import os
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class UnifiedLLM:
    """Unified async interface across providers."""

    def __init__(self, provider: Optional[str] = None, model_name: Optional[str] = None):
        self.provider = (provider or os.getenv("MODEL_PROVIDER", "groq")).lower()
        # Prefer alias (e.g., openai/gpt-oss-120b), then GROQ_MODEL, then default
        self.model_name = (
            model_name
            or os.getenv("GROQ_MODEL_ALIAS")
            or os.getenv("GROQ_MODEL")
            or "openai/gpt-oss-120b"
        )

        if self.provider == "groq":
            self._init_groq()
        elif self.provider == "huggingface":
            self._init_huggingface()
        else:
            raise ValueError(f"Unsupported MODEL_PROVIDER: {self.provider}")

    def _init_groq(self) -> None:
        try:
            from groq import Groq  # type: ignore
        except Exception as e:
            raise ImportError("groq package is required. Install with: pip install groq") from e

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for Groq provider")

        # Model name already resolved in __init__ (alias > model > default)

        self._groq_client = Groq(api_key=api_key)
        logger.info(f"✅ Groq initialized with model: {self.model_name}")

    def _init_huggingface(self) -> None:
        self._hf_url = os.getenv(
            "HF_MODEL_URL",
            "https://router.huggingface.co/hf-inference/models/meta-llama/Llama-3.2-3B-Instruct",
        )
        self._hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not self._hf_token:
            raise ValueError("HUGGINGFACE_TOKEN environment variable is required for HuggingFace provider")
        logger.info(f"✅ HuggingFace initialized: {self._hf_url}")

    async def generate_content_async(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048):
        """Generate content with a Gemini-compatible response object (has .text)."""
        if self.provider == "groq":
            return await self._groq_generate(prompt, temperature, max_tokens)
        elif self.provider == "huggingface":
            return await self._hf_generate(prompt, max_tokens)
        else:
            raise RuntimeError(f"Unsupported provider at runtime: {self.provider}")

    async def _groq_generate(self, prompt: str, temperature: float, max_tokens: int):
        import asyncio

        def _call():
            try:
                return self._groq_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.error(f"Groq API call failed: {e}")
                # Rate limit durumunda basit yanıt döndür
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    logger.warning("Rate limit reached, using fallback response")
                    class FallbackResponse:
                        def __init__(self):
                            self.choices = [type('Choice', (), {
                                'message': type('Message', (), {
                                    'content': "Rate limit nedeniyle LLM yanıtı oluşturulamadı. Lütfen daha sonra tekrar deneyin."
                                })()
                            })()]
                    return FallbackResponse()
                raise

        response = await asyncio.get_event_loop().run_in_executor(None, _call)

        class Response:
            def __init__(self, text: str):
                self.text = text

        text = response.choices[0].message.content if response.choices else ""
        return Response(text or "")

    async def _hf_generate(self, prompt: str, max_tokens: int):
        import httpx

        headers = {"Authorization": f"Bearer {self._hf_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.7,
                "return_full_text": False,
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self._hf_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                text = data[0].get("generated_text", "")
            else:
                text = data.get("generated_text", "")

        class Response:
            def __init__(self, text: str):
                self.text = text

        return Response(text or "")


