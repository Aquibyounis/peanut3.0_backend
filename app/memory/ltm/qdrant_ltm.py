"""
Qdrant-based Long-Term Memory (LTM).

Stores persistent user memories in a dedicated Qdrant collection
(``peanut_user_memory``), separate from the RAG knowledge base.
Supports semantic search scoped to individual users, with memory
type classification and importance scoring.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.logging.logger import get_logger
from app.rag.embeddings import generate_embedding
from app.rag.qdrant_client import client

logger = get_logger(__name__)

USER_MEMORY_COLLECTION = "peanut_user_memory"
VECTOR_SIZE = 768

VALID_MEMORY_TYPES = frozenset(
    {"fact", "preference", "project", "conversation", "architecture"}
)


def _ensure_collection() -> None:
    """Create the user-memory collection if it does not exist (sync)."""
    collections = client.get_collections()
    existing = [c.name for c in collections.collections]
    if USER_MEMORY_COLLECTION not in existing:
        client.create_collection(
            collection_name=USER_MEMORY_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created Qdrant collection",
            collection=USER_MEMORY_COLLECTION,
        )


# Initialise collection at import time (matches existing qdrant_client.py pattern)
try:
    _ensure_collection()
except Exception as exc:
    logger.warning(
        "Could not ensure user-memory collection on import — will retry at runtime",
        error=str(exc),
    )


class QdrantLTM:
    """Long-Term Memory backed by Qdrant vector store."""

    def __init__(self) -> None:
        self._collection = USER_MEMORY_COLLECTION

    async def _ensure_ready(self) -> None:
        """Lazily ensure the collection exists (handles deferred startup)."""
        try:
            await asyncio.to_thread(_ensure_collection)
        except Exception as exc:
            logger.error("Failed to ensure LTM collection", error=str(exc))

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "fact",
        metadata: Optional[dict] = None,
        importance_score: float = 0.5,
    ) -> Optional[str]:
        """Embed *content* and upsert into Qdrant.  Returns the point ID."""
        await self._ensure_ready()

        if memory_type not in VALID_MEMORY_TYPES:
            memory_type = "fact"

        embedding = await asyncio.to_thread(generate_embedding, content)
        if embedding is None:
            logger.error("Embedding generation failed for LTM store")
            return None

        point_id = str(uuid.uuid4())
        payload: dict = {
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "importance_score": importance_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            payload["metadata"] = metadata

        await asyncio.to_thread(
            client.upsert,
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        logger.info(
            "LTM memory stored",
            user_id=user_id,
            point_id=point_id,
            memory_type=memory_type,
        )
        return point_id

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        memory_type_filter: Optional[str] = None,
    ) -> list[dict]:
        """Semantic search over a user's memories."""
        await self._ensure_ready()

        embedding = await asyncio.to_thread(generate_embedding, query)
        if embedding is None:
            logger.error("Embedding generation failed for LTM search")
            return []

        must_conditions: list[FieldCondition] = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]
        if memory_type_filter and memory_type_filter in VALID_MEMORY_TYPES:
            must_conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchValue(value=memory_type_filter),
                )
            )

        results = await asyncio.to_thread(
            client.query_points,
            collection_name=self._collection,
            query=embedding,
            query_filter=Filter(must=must_conditions),
            limit=limit,
        )

        memories: list[dict] = []
        for point in results.points:
            memories.append(
                {
                    "id": str(point.id),
                    "content": point.payload.get("content", ""),
                    "memory_type": point.payload.get("memory_type", "fact"),
                    "importance_score": point.payload.get(
                        "importance_score", 0.5
                    ),
                    "created_at": point.payload.get("created_at", ""),
                    "score": point.score,
                    "metadata": point.payload.get("metadata"),
                }
            )
        return memories

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_memory(self, user_id: str, point_id: str) -> bool:
        """Delete a specific memory point owned by *user_id*."""
        try:
            await asyncio.to_thread(
                client.delete,
                collection_name=self._collection,
                points_selector=[point_id],
            )
            logger.info(
                "LTM memory deleted",
                user_id=user_id,
                point_id=point_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "Failed to delete LTM memory",
                user_id=user_id,
                point_id=point_id,
                error=str(exc),
            )
            return False

    # ------------------------------------------------------------------
    # Scroll / list
    # ------------------------------------------------------------------

    async def get_user_memories(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Scroll all memories for a user (no query vector needed)."""
        await self._ensure_ready()

        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        )

        results, _next_offset = await asyncio.to_thread(
            client.scroll,
            collection_name=self._collection,
            scroll_filter=scroll_filter,
            limit=limit,
        )

        memories: list[dict] = []
        for point in results:
            memories.append(
                {
                    "id": str(point.id),
                    "content": point.payload.get("content", ""),
                    "memory_type": point.payload.get("memory_type", "fact"),
                    "importance_score": point.payload.get(
                        "importance_score", 0.5
                    ),
                    "created_at": point.payload.get("created_at", ""),
                    "metadata": point.payload.get("metadata"),
                }
            )
        return memories
