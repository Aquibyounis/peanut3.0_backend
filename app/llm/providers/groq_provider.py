"""
Peanut 3.0 - Groq Provider (Direct HTTP, no OpenAI SDK)
"""

import asyncio
import time
import json
import httpx
import requests
from typing import AsyncGenerator, Any

from app.core.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class GroqProvider:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.default_model = settings.groq_model

        # Groq endpoint configuration (no OpenAI SDK)
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Asynchronously call Groq API with retries and exponential backoff using httpx."""
        model = model or self.default_model
        retries = 3
        delay = 1.0
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        for attempt in range(retries):
            try:
                start_time = time.time()
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=self.headers,
                    )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"] or ""
                latency = time.time() - start_time
                logger.info(
                    "Groq completion success",
                    model=model,
                    latency_seconds=round(latency, 3),
                    attempt=attempt + 1,
                )
                return content
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    logger.warning(
                        "Groq rate limit hit (429)",
                        model=model,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(delay * (2 ** attempt))
                else:
                    logger.error(
                        "Groq API HTTP error",
                        model=model,
                        status=status,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(delay)
            except httpx.TimeoutException as e:
                logger.warning(
                    "Groq API timeout",
                    model=model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(delay)
            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.error(
                    "Groq API connection error",
                    model=model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(delay)
        return ""

    def generate_sync(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Synchronously call Groq API with retries using requests."""
        model = model or self.default_model
        retries = 3
        delay = 1.0
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        for attempt in range(retries):
            try:
                start_time = time.time()
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"] or ""
                latency = time.time() - start_time
                logger.info(
                    "Groq sync completion success",
                    model=model,
                    latency_seconds=round(latency, 3),
                    attempt=attempt + 1,
                )
                return content
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status == 429:
                    logger.warning(
                        "Groq sync rate limit hit (429)",
                        model=model,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt == retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
                else:
                    logger.error(
                        "Groq sync API HTTP error",
                        model=model,
                        status=status,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt == retries - 1:
                        raise
                    time.sleep(delay)
            except requests.exceptions.Timeout as e:
                logger.warning(
                    "Groq sync API timeout",
                    model=model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == retries - 1:
                    raise
                time.sleep(delay)
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    "Groq sync API connection error",
                    model=model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == retries - 1:
                    raise
                time.sleep(delay)
        return ""

    async def generate_stream(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Asynchronously stream tokens from Groq API using httpx streaming."""
        model = model or self.default_model
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            if raw_data == "[DONE]":
                                break
                            try:
                                data = json.loads(raw_data)
                                if "choices" in data:
                                    delta = data["choices"][0].get("delta", {})
                                    if delta.get("content"):
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error("Groq streaming error", model=model, error=str(e))
            raise e
