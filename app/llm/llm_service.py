"""
Peanut 3.0 - Unified LLM Orchestration Service
"""

import time
from typing import AsyncGenerator, Optional
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.fallback_provider import FallbackProvider
from app.llm.providers.model_router import ModelRouter
from app.llm.prompts.system_prompts import build_system_prompt
from app.llm.streaming.stream_handler import StreamHandler
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class LLMService:
    def __init__(self):
        self.groq_provider = GroqProvider()
        self.fallback_provider = FallbackProvider(self.groq_provider)
        self.router = ModelRouter()
        self.stream_handler = StreamHandler(self.groq_provider)

    async def generate_chat_response(
        self,
        query: str,
        context: str,
        chat_history: Optional[list] = None,
        task_type: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024
    ) -> str:
        """Generate a complete chat response via Groq API with RAG context and fallback support."""
        start_time = time.time()
        
        # 1. Build system prompt and format messages
        system_prompt = build_system_prompt(query, context)
        messages = [{"role": "system", "content": system_prompt}]
        
        if chat_history:
            for msg in chat_history:
                role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                if role and content:
                    # Strip any lingering follow-up tags from history
                    if "<follow_ups>" in content:
                        content = content.split("<follow_ups>")[0].strip()
                    messages.append({"role": role, "content": content})
                    
        messages.append({"role": "user", "content": query})
        
        # 2. Select optimized model
        selected_model = self.router.get_model_for_task(task_type) if task_type else self.router.route_for_query(query)
        
        logger.info(
            "Generating response",
            selected_model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 3. Call fallback provider
        try:
            content = await self.fallback_provider.generate_with_fallback(
                messages=messages,
                model=selected_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            latency = time.time() - start_time
            logger.info(
                "Response generated successfully",
                latency_seconds=round(latency, 3),
                response_length=len(content)
            )
            return content
        except Exception as e:
            logger.critical("LLM Service generation failed completely", error=str(e))
            raise e

    async def stream_chat_response(
        self,
        query: str,
        context: str,
        chat_history: Optional[list] = None,
        task_type: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        is_sse: bool = False
    ) -> AsyncGenerator[str, None]:
        """Stream chat tokens via Groq API with dynamic model routing, fallback switching, and follow-ups."""
        start_time = time.time()
        
        # 1. Build system prompt and format messages
        system_prompt = build_system_prompt(query, context)
        messages = [{"role": "system", "content": system_prompt}]
        
        if chat_history:
            for msg in chat_history:
                role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                if role and content:
                    # Strip any lingering follow-up tags from history
                    if "<follow_ups>" in content:
                        content = content.split("<follow_ups>")[0].strip()
                    messages.append({"role": role, "content": content})
                    
        messages.append({"role": "user", "content": query})
        
        # 2. Select optimized model
        selected_model = self.router.get_model_for_task(task_type) if task_type else self.router.route_for_query(query)
        
        logger.info(
            "Streaming response initialized",
            selected_model=selected_model,
            is_sse=is_sse
        )
        
        # 3. Obtain the raw fallback-supported token stream
        raw_stream = self.fallback_provider.generate_stream_with_fallback(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 4. Wrap with StreamHandler to automatically inject follow-up chips at completion
        if is_sse:
            async for chunk in self.stream_handler.stream_sse(raw_stream, query, context):
                yield chunk
        else:
            async for chunk in self.stream_handler.stream_raw(raw_stream, query, context):
                yield chunk
                
        latency = time.time() - start_time
        logger.info("Streaming response stream closed", duration_seconds=round(latency, 3))
        
# Unified service instance
llm_service = LLMService()
