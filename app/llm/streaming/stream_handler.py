"""
Peanut 3.0 - Unified Stream Handler
Manages FastAPI StreamingResponse and SSE event formatting.
Appends XML follow-ups at the end of plain-text streams.
"""

import json
from typing import AsyncGenerator
from app.llm.prompts.context_prompts import build_followup_prompt
from app.llm.providers.groq_provider import GroqProvider
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class StreamHandler:
    def __init__(self, groq_provider: GroqProvider):
        self.provider = groq_provider

    async def stream_raw(self, stream_generator: AsyncGenerator[str, None], query: str, context: str = "") -> AsyncGenerator[str, None]:
        """Stream plain-text tokens and append the <follow_ups> block at the end."""
        full_response_parts = []
        
        async for token in stream_generator:
            full_response_parts.append(token)
            yield token
            
        full_response = "".join(full_response_parts)
        
        # Stream completes -> generate follow ups asynchronously via Groq
        try:
            logger.info("Generating follow-up questions via Groq")
            followups = await self.generate_followups(query, full_response, context)
            if followups:
                followup_xml = f"\n\n<follow_ups>{json.dumps(followups)}</follow_ups>"
                yield followup_xml
        except Exception as e:
            logger.warning("Failed to append follow-ups to stream", error=str(e))
            
    async def stream_sse(self, stream_generator: AsyncGenerator[str, None], query: str, context: str = "") -> AsyncGenerator[str, None]:
        """Stream tokens formatted as Server-Sent Events (SSE)."""
        full_response_parts = []
        
        async for token in stream_generator:
            full_response_parts.append(token)
            yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
            
        full_response = "".join(full_response_parts)
        
        # Send follow ups
        try:
            followups = await self.generate_followups(query, full_response, context)
            if followups:
                yield f"data: {json.dumps({'event': 'follow_up', 'data': followups})}\n\n"
        except Exception as e:
            logger.warning("Failed to stream follow-ups via SSE", error=str(e))
            
        yield "data: {\"event\": \"done\", \"data\": \"\"}\n\n"

    async def generate_followups(self, query: str, response: str, context: str = "") -> list[str]:
        """Call Groq synchronously/asynchronously to generate exactly 3 contextual follow-ups."""
        prompt = build_followup_prompt(query, response, context)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            raw_output = await self.provider.generate(
                messages=messages,
                model="llama-3.1-8b-instant", # fast chat model
                temperature=0.5,
                max_tokens=150
            )
            
            questions = []
            
            # 1. Attempt JSON list extraction
            start = raw_output.find("[")
            end = raw_output.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    parsed = json.loads(raw_output[start:end])
                    if isinstance(parsed, list):
                        questions = [str(q).strip() for q in parsed if str(q).strip()]
                except Exception:
                    pass
            
            # 2. If JSON extraction failed or didn't yield enough items, parse line-by-line
            if len(questions) < 3:
                import re
                lines = raw_output.split("\n")
                extracted = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # Remove markdown bullets, numbering (e.g., "1.", "- ", "* ")
                    line = re.sub(r'^(?:\d+\.|\*|-)\s*', '', line).strip()
                    # Strip wrapping quotes if any
                    line = re.sub(r'^["\']|["\']$', '', line).strip()
                    if line and (line.endswith("?") or len(line) > 10):
                        extracted.append(line)
                if len(extracted) >= 3:
                    questions = extracted
            
            if len(questions) >= 3:
                return [q for q in questions[:3]]
                
        except Exception as e:
            logger.warning("Groq follow-up generation failed, utilizing fallback", error=str(e))
            
        # Fallback list
        return [
            "Can you tell me more about this?",
            "What technologies are involved?",
            "How does this compare to similar projects?",
        ]
