from app.rag.qdrant_client import (
    client,
    COLLECTION_NAME
)

client.delete_collection(
    collection_name=COLLECTION_NAME
)

print("Collection deleted.")