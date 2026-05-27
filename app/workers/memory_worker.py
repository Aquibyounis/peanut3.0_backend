"""
Peanut 3.0 - Memory Worker
Background tasks for extracting facts, building LTM, and consolidating memories.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.logger import get_logger
from app.core.postgres.database import AsyncSessionLocal
from app.models.memory import MemoryMetadata
from app.models.message import Message
from app.models.session import Session

logger = get_logger(__name__)

# ── Fact-extraction heuristics ──

_FACT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:I am|I'm|my name is)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:I work at|I work for|employed at)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:I live in|I'm from|I am from)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:I like|I love|I enjoy|I prefer)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:I use|I'm using|I prefer using)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:my favorite|my preferred)\b\s+(.+)", re.IGNORECASE),
    re.compile(r"\b(?:I studied|I graduated from|my degree is)\b\s+(.+)", re.IGNORECASE),
]

_IMPORTANT_KEYWORDS: list[str] = [
    "important",
    "remember",
    "note",
    "always",
    "never",
    "deadline",
    "birthday",
    "anniversary",
    "password",
    "account",
    "project",
    "goal",
    "plan",
]


def extract_important_facts(conversation_text: str) -> list[str]:
    """
    Extract important facts from conversation text using pattern matching
    and keyword analysis.

    Returns a deduplicated list of fact strings.
    """
    facts: list[str] = []

    # Pattern-based extraction
    for pattern in _FACT_PATTERNS:
        matches = pattern.findall(conversation_text)
        for match in matches:
            cleaned = match.strip().rstrip(".!?,;:")
            if len(cleaned) > 3:
                facts.append(cleaned)

    # Keyword-based sentence extraction
    sentences = re.split(r"[.!?\n]+", conversation_text)
    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if any(kw in sentence_lower for kw in _IMPORTANT_KEYWORDS):
            cleaned_sentence = sentence.strip()
            if 5 < len(cleaned_sentence) < 500:
                facts.append(cleaned_sentence)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_facts: list[str] = []
    for fact in facts:
        normalised = fact.lower().strip()
        if normalised not in seen:
            seen.add(normalised)
            unique_facts.append(fact)

    return unique_facts


async def process_conversation_for_ltm(
    user_id: str,
    session_id: str,
    messages: list[dict[str, str]],
) -> list[str]:
    """
    Process a conversation's messages, extract facts, and store as LTM entries.

    Parameters
    ----------
    user_id : str (UUID string)
    session_id : str (UUID string)
    messages : list of dicts with 'role' and 'content' keys

    Returns
    -------
    list[str] — the extracted facts that were persisted.
    """
    import uuid as _uuid

    # Build single text block from user messages
    user_texts = [
        msg["content"] for msg in messages if msg.get("role") == "user" and msg.get("content")
    ]
    if not user_texts:
        logger.info("No user messages to process for LTM", session_id=session_id)
        return []

    conversation_text = "\n".join(user_texts)
    facts = extract_important_facts(conversation_text)

    if not facts:
        logger.info("No important facts extracted", session_id=session_id)
        return []

    logger.info(
        "Extracted facts for LTM",
        user_id=user_id,
        session_id=session_id,
        fact_count=len(facts),
    )

    try:
        async with AsyncSessionLocal() as db:
            for fact in facts:
                memory = MemoryMetadata(
                    user_id=_uuid.UUID(user_id),
                    memory_type="ltm",
                    content=fact,
                    metadata_json={
                        "source": "conversation_extraction",
                        "session_id": session_id,
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(memory)
            await db.commit()
            logger.info("LTM facts persisted", count=len(facts))
    except Exception as exc:
        logger.error("Failed to persist LTM facts", error=str(exc))

    return facts


async def run_periodic_consolidation() -> dict[str, Any]:
    """
    Consolidate old STM entries into LTM.

    Strategy: find STM memories older than 24 hours, group by user,
    merge overlapping content, and re-persist as LTM entries.

    Returns a summary dict.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    consolidated_count = 0

    try:
        async with AsyncSessionLocal() as db:
            # Fetch stale STM entries
            stmt = (
                select(MemoryMetadata)
                .where(
                    MemoryMetadata.memory_type == "stm",
                    MemoryMetadata.created_at < cutoff,
                )
                .order_by(MemoryMetadata.user_id, MemoryMetadata.created_at)
            )
            result = await db.execute(stmt)
            stm_entries = result.scalars().all()

            if not stm_entries:
                logger.info("No stale STM entries to consolidate")
                return {"consolidated": 0, "users_processed": 0}

            # Group by user
            user_groups: dict[str, list[MemoryMetadata]] = {}
            for entry in stm_entries:
                uid = str(entry.user_id)
                user_groups.setdefault(uid, []).append(entry)

            for uid, entries in user_groups.items():
                import uuid as _uuid

                # Merge content
                merged_content = "\n---\n".join(e.content for e in entries)

                # Extract consolidated facts
                facts = extract_important_facts(merged_content)

                # If no extractable facts, keep the raw merged text
                if not facts:
                    facts = [merged_content[:2000]]

                for fact in facts:
                    ltm = MemoryMetadata(
                        user_id=_uuid.UUID(uid),
                        memory_type="ltm",
                        content=fact,
                        metadata_json={
                            "source": "stm_consolidation",
                            "original_stm_count": len(entries),
                            "consolidated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    db.add(ltm)

                # Delete original STM entries
                for entry in entries:
                    await db.delete(entry)

                consolidated_count += len(entries)

            await db.commit()

            summary = {
                "consolidated": consolidated_count,
                "users_processed": len(user_groups),
            }
            logger.info("STM consolidation complete", **summary)
            return summary

    except Exception as exc:
        logger.error("STM consolidation failed", error=str(exc))
        return {"consolidated": 0, "users_processed": 0, "error": str(exc)}
