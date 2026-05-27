"""
Memory orchestration layer.

Coordinates Short-Term Memory (Redis) and Long-Term Memory (Qdrant)
to build unified conversation context.  Also handles the store-side:
persisting exchanges and extracting durable facts from conversations.
"""

import re
from typing import Optional

from app.core.logging.logger import get_logger
from app.memory.ltm.qdrant_ltm import QdrantLTM
from app.memory.router import MemoryRoute, MemoryRouter
from app.memory.stm.redis_stm import RedisSTM

logger = get_logger(__name__)

# Singleton instances
_stm = RedisSTM()
_ltm = QdrantLTM()
_router = MemoryRouter()

# ── Patterns that hint at important, storable facts ──────────────────
_FACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:i (?:am|work|use|prefer|like|need|want|have|build|live))\b", re.I),
    re.compile(r"\b(?:my (?:name|job|project|stack|preference|team|company))\b", re.I),
    re.compile(r"\b(?:we (?:decided|agreed|chose|selected|use|switched))\b", re.I),
    re.compile(r"\b(?:the (?:architecture|design|plan|approach) (?:is|was|will be))\b", re.I),
    re.compile(r"\b(?:important|remember this|keep in mind|note that|fyi)\b", re.I),
]

_MIN_LENGTH_FOR_AUTO_LTM = 120  # characters — short messages rarely contain durable facts


class MemoryOrchestrator:
    """Unified facade over STM + LTM with automatic routing."""

    # ── Context retrieval ────────────────────────────────────────────

    async def get_context(
        self,
        user_id: str,
        session_id: str,
        query: str,
        message_count: int = 0,
    ) -> str:
        """Build a combined context string from the appropriate memory tiers."""
        route = await _router.route(query, message_count=message_count)

        if route == MemoryRoute.IGNORE:
            return ""

        if route == MemoryRoute.SUMMARIZE:
            summary = await _stm.get_summary(user_id, session_id)
            if summary:
                return f"[Conversation Summary]\n{summary}"
            # Fall through to STM if no summary is stored yet
            stm_ctx = await _stm.get_context_window(user_id, session_id)
            return stm_ctx

        # STM context (always when not IGNORE)
        stm_context = await _stm.get_context_window(
            user_id, session_id, max_tokens=1500
        )

        if route == MemoryRoute.STM_ONLY:
            return stm_context

        # STM_AND_LTM — merge both
        ltm_memories = await _ltm.search_memories(
            user_id=user_id,
            query=query,
            limit=5,
        )

        parts: list[str] = []

        if stm_context:
            parts.append("[Recent Conversation]\n" + stm_context)

        if ltm_memories:
            ltm_lines = [
                f"- [{m['memory_type']}] {m['content']}"
                for m in ltm_memories
            ]
            parts.append(
                "[Long-Term Memory]\n" + "\n".join(ltm_lines)
            )

        return "\n\n".join(parts)

    # ── Store side ───────────────────────────────────────────────────

    async def store_exchange(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Persist a user↔assistant exchange in STM and conditionally in LTM."""
        # Always store both turns in STM
        await _stm.store_message(user_id, session_id, "user", user_message)
        await _stm.store_message(
            user_id, session_id, "assistant", assistant_response
        )

        # Try to extract and persist durable facts
        facts = self.extract_facts(user_message, assistant_response)
        for fact in facts:
            await _ltm.store_memory(
                user_id=user_id,
                content=fact,
                memory_type=self._classify_fact(fact),
                importance_score=0.6,
            )

        logger.debug(
            "Exchange stored",
            user_id=user_id,
            session_id=session_id,
            facts_extracted=len(facts),
        )

    # ── Fact extraction (heuristic) ──────────────────────────────────

    @staticmethod
    def extract_facts(
        user_message: str, assistant_response: str
    ) -> list[str]:
        """Extract durable facts worth remembering from an exchange.

        Uses simple heuristics:
        1. Long user messages that match fact-like patterns.
        2. Statements containing explicit preference / architecture signals.
        """
        facts: list[str] = []

        # Analyse user message
        if len(user_message) >= _MIN_LENGTH_FOR_AUTO_LTM:
            for pattern in _FACT_PATTERNS:
                if pattern.search(user_message):
                    facts.append(user_message.strip())
                    break  # one hit is enough for the whole message

        # Also scan for short, high-signal statements
        for sentence in re.split(r"[.!?\n]", user_message):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            for pattern in _FACT_PATTERNS:
                if pattern.search(sentence):
                    if sentence not in facts:
                        facts.append(sentence)
                    break

        # Cap the number of facts per exchange
        return facts[:5]

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _classify_fact(fact: str) -> str:
        """Naive classification of a fact string into a memory type."""
        lower = fact.lower()
        if any(
            kw in lower
            for kw in ("prefer", "like", "favorite", "rather", "always use")
        ):
            return "preference"
        if any(
            kw in lower
            for kw in ("project", "repo", "codebase", "build", "app")
        ):
            return "project"
        if any(
            kw in lower
            for kw in (
                "architecture",
                "design",
                "pattern",
                "stack",
                "infrastructure",
            )
        ):
            return "architecture"
        return "fact"

    # ── Expose sub-systems for direct access when needed ─────────────

    @property
    def stm(self) -> RedisSTM:
        return _stm

    @property
    def ltm(self) -> QdrantLTM:
        return _ltm
