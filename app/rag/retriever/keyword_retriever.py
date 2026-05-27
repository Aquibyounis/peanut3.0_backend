import asyncio
from qdrant_client.models import Filter, FieldCondition, MatchText
from app.rag.qdrant_client import client, COLLECTION_NAME

class KeywordRetriever:
    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        must_filters = [FieldCondition(key="text", match=MatchText(text=query))]
        query_filter = Filter(must=must_filters)
        
        # We use scroll for keyword search on text field
        results, _ = await asyncio.to_thread(
            client.scroll,
            collection_name=COLLECTION_NAME,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True
        )
        
        contexts = []
        for point in results:
            contexts.append({
                "text": point.payload.get("text", ""),
                "title": point.payload.get("title", ""),
                "chunk_type": point.payload.get("chunk_type", ""),
                "score": 1.0, # Dummy score for BM25/keyword
                "metadata": point.payload
            })
            
        return contexts
