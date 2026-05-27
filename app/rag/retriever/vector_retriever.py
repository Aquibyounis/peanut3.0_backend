import asyncio
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.rag.qdrant_client import client, COLLECTION_NAME
from app.rag.embeddings import generate_embedding

class VectorRetriever:
    async def retrieve(self, query: str, limit: int = 5, score_threshold: float = 0.0, metadata_filters: dict | None = None) -> list[dict]:
        query_embedding = await asyncio.to_thread(generate_embedding, query)
        
        must_filters = []
        if metadata_filters:
            for key, value in metadata_filters.items():
                must_filters.append(FieldCondition(key=f"payload.{key}", match=MatchValue(value=value)))
                
        query_filter = Filter(must=must_filters) if must_filters else None
        
        results = await asyncio.to_thread(
            client.query_points,
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )
        
        contexts = []
        for point in results.points:
            contexts.append({
                "text": point.payload.get("text", ""),
                "title": point.payload.get("title", ""),
                "chunk_type": point.payload.get("chunk_type", ""),
                "score": point.score,
                "metadata": point.payload
            })
            
        return contexts
