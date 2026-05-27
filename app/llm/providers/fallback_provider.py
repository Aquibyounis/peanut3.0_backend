"""
Peanut 3.0 - Fallback Provider
Resilient model failover logic in case of rate limits or service outages.
"""

from typing import AsyncGenerator
from app.llm.providers.groq_provider import GroqProvider
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

# Resilient fallback chain
FALLBACK_CHAIN = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "qwen-qwq-32b",
    "gemma2-9b-it"
]

class FallbackProvider:
    def __init__(self, groq_provider: GroqProvider):
        self.provider = groq_provider

    async def generate_with_fallback(self, messages: list[dict], model: str = None, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        """Attempt completion with model, fallback to others in case of failures."""
        primary_model = model or self.provider.default_model
        
        # Build dynamic fallback list starting with the requested model
        models_to_try = [primary_model]
        for m in FALLBACK_CHAIN:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for current_model in models_to_try:
            try:
                logger.info("Attempting generation", model=current_model)
                content = await self.provider.generate(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if content:
                    return content
            except Exception as e:
                last_error = e
                logger.warning(
                    "Model execution failed, trying next fallback model",
                    failed_model=current_model,
                    error=str(e)
                )
                continue
                
        # If all fail, raise the last exception
        logger.critical("All fallback models exhausted and failed.")
        if last_error:
            raise last_error
        raise RuntimeError("Fallback provider failed to generate response.")

    async def generate_stream_with_fallback(self, messages: list[dict], model: str = None, temperature: float = 0.3, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        """Stream tokens with model, failover to fallback models if stream initialization fails."""
        primary_model = model or self.provider.default_model
        
        models_to_try = [primary_model]
        for m in FALLBACK_CHAIN:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        stream_started = False
        
        for current_model in models_to_try:
            try:
                logger.info("Attempting streaming generation", model=current_model)
                stream = self.provider.generate_stream(
                    messages=messages,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Verify we can extract the first chunk (stream starts successfully)
                async for chunk in stream:
                    stream_started = True
                    yield chunk
                    
                # If we successfully run the entire stream, we exit
                if stream_started:
                    return
                    
            except Exception as e:
                last_error = e
                # If the stream had already started, we cannot easily fallback mid-stream
                if stream_started:
                    logger.error("Streaming interrupted mid-stream", model=current_model, error=str(e))
                    yield "\n\n⚠️ Streaming connection interrupted."
                    return
                    
                logger.warning(
                    "Stream initialization failed, trying next fallback model",
                    failed_model=current_model,
                    error=str(e)
                )
                continue

        # If all fail to even start, raise last error
        logger.critical("All fallback streams exhausted and failed.")
        if last_error:
            raise last_error
        yield "\n\n⚠️ Service temporarily unavailable."
