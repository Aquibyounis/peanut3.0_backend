"""
Peanut 3.0 - Qdrant Client

Production: Qdrant Cloud (API key authentication).
Development: Local Qdrant via docker-compose.
"""

from qdrant_client import QdrantClient

from qdrant_client.models import (
    VectorParams,
    Distance
)

from app.core.config import settings

# Connect with API key when available (Qdrant Cloud), otherwise local
client_kwargs = {"url": settings.qdrant_url}
if settings.qdrant_api_key:
    client_kwargs["api_key"] = settings.qdrant_api_key

client = QdrantClient(**client_kwargs)

COLLECTION_NAME = "peanut_memory"


collections = client.get_collections()

existing_collections = [
    c.name
    for c in collections.collections
]


if COLLECTION_NAME not in existing_collections:

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )

    print(
        f"Created collection: {COLLECTION_NAME}"
    )

else:

    print(
        f"Using collection: {COLLECTION_NAME}"
    )