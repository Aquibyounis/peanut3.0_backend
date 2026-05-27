"""
Memory routing logic.

Examines an incoming query and decides which memory subsystems
(STM, LTM, or neither) should be consulted when building context.
"""

from enum import Enum

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class MemoryRoute(Enum):
    STM_ONLY = "stm_only"
    STM_AND_LTM = "stm_and_ltm"
    IGNORE = "ignore"
    SUMMARIZE = "summarize"


class MemoryRouter:
    """Routes queries to appropriate memory systems."""

    # Keywords that suggest LTM retrieval is needed
    LTM_TRIGGERS: list[str] = [
        "remember",
        "previously",
        "earlier",
        "before",
        "last time",
        "you said",
        "we discussed",
        "my preference",
        "i told you",
        "recall",
        "history",
        "past",
        "mentioned",
    ]

    # Keywords that suggest memory should be ignored
    IGNORE_TRIGGERS: list[str] = [
        "hello",
        "hi",
        "hey",
        "thanks",
        "thank you",
        "bye",
        "good morning",
        "good night",
        "ok",
        "okay",
    ]

    SUMMARIZE_TRIGGERS: list[str] = [
        "summarize",
        "summary",
        "overview",
        "recap",
        "brief",
    ]

    async def route(
        self, query: str, message_count: int = 0
    ) -> MemoryRoute:
        """Determine which memory systems to query."""
        query_lower = query.lower().strip()

        # Check for ignore triggers (greetings, pleasantries)
        if (
            any(trigger in query_lower for trigger in self.IGNORE_TRIGGERS)
            and len(query_lower.split()) < 5
        ):
            logger.debug("Memory route: IGNORE", query=query[:50])
            return MemoryRoute.IGNORE

        # Check for summarize triggers
        if any(trigger in query_lower for trigger in self.SUMMARIZE_TRIGGERS):
            logger.debug("Memory route: SUMMARIZE", query=query[:50])
            return MemoryRoute.SUMMARIZE

        # Check for LTM triggers
        if any(trigger in query_lower for trigger in self.LTM_TRIGGERS):
            logger.debug("Memory route: STM_AND_LTM", query=query[:50])
            return MemoryRoute.STM_AND_LTM

        # Default: use STM for context continuity
        if message_count > 2:
            return MemoryRoute.STM_AND_LTM

        return MemoryRoute.STM_ONLY
