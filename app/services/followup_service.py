"""
Peanut 3.0 - Contextual Follow-up Questions Service
Delegates to the unified llm_service StreamHandler for Groq-powered contextual follow-ups.
"""

from app.llm.llm_service import llm_service

class FollowupService:
    """Generates context-aware follow-up questions via Groq."""

    async def generate_followups(
        self,
        query: str,
        response: str,
        context: str = "",
    ) -> list[str]:
        """Generate 3 contextual follow-up questions using Groq API."""
        return await llm_service.stream_handler.generate_followups(
            query=query,
            response=response,
            context=context
        )
