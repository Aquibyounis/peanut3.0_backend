"""
Peanut 3.0 - Groq Provider (OpenAI SDK compatible)
"""

import asyncio
import time
from typing import AsyncGenerator, Any
from openai import AsyncOpenAI, OpenAI
from openai import APIConnectionError, RateLimitError, APITimeoutError, APIStatusError

from app.core.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class GroqProvider:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.default_model = settings.groq_model
        
        # Groq endpoint is OpenAI compatible
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0
        )
        self.sync_client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0
        )

    async def generate(self, messages: list[dict], model: str = None, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Asynchronously call Groq API with retries and exponential backoff."""
        model = model or self.default_model
        retries = 3
        delay = 1.0
        
        for attempt in range(retries):
            try:
                start_time = time.time()
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages, # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                latency = time.time() - start_time
                content = response.choices[0].message.content or ""
                
                logger.info(
                    "Groq completion success",
                    model=model,
                    latency_seconds=round(latency, 3),
                    attempt=attempt + 1,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0
                )
                return content
                
            except RateLimitError as e:
                logger.warning("Groq rate limit hit (429)", model=model, attempt=attempt + 1, error=str(e))
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(delay * (2 ** attempt)) # exponential backoff
                
            except APITimeoutError as e:
                logger.warning("Groq API timeout", model=model, attempt=attempt + 1, error=str(e))
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(delay)
                
            except (APIConnectionError, APIStatusError) as e:
                logger.error("Groq API error", model=model, attempt=attempt + 1, error=str(e))
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(delay)

        return ""

    def generate_sync(self, messages: list[dict], model: str = None, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Synchronously call Groq API with retries."""
        model = model or self.default_model
        retries = 3
        delay = 1.0
        
        for attempt in range(retries):
            try:
                start_time = time.time()
                response = self.sync_client.chat.completions.create(
                    model=model,
                    messages=messages, # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                latency = time.time() - start_time
                content = response.choices[0].message.content or ""
                
                logger.info(
                    "Groq sync completion success",
                    model=model,
                    latency_seconds=round(latency, 3),
                    attempt=attempt + 1
                )
                return content
                
            except RateLimitError as e:
                logger.warning("Groq sync rate limit hit (429)", model=model, attempt=attempt + 1, error=str(e))
                if attempt == retries - 1:
                    raise e
                time.sleep(delay * (2 ** attempt))
                
            except (APITimeoutError, APIConnectionError, APIStatusError) as e:
                logger.error("Groq sync API error", model=model, attempt=attempt + 1, error=str(e))
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)
                
        return ""

    async def generate_stream(self, messages: list[dict], model: str = None, temperature: float = 0.3, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        """Asynchronously stream tokens from Groq API."""
        model = model or self.default_model
        
        try:
            start_time = time.time()
            response_stream = await self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            logger.info("Groq stream initialized", model=model)
            
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
            latency = time.time() - start_time
            logger.info("Groq stream completed", model=model, duration_seconds=round(latency, 3))
            
        except Exception as e:
            logger.error("Groq streaming error", model=model, error=str(e))
            raise e
