import time
import asyncio
from app.rag.query_rewriter import rewrite_query
from app.rag.retriever.hybrid_retriever import HybridRetriever
from app.rag.reranker.reranker import Reranker
from app.rag.context_builder.builder import ContextBuilder

class RAGPipeline:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.reranker = Reranker()
        self.builder = ContextBuilder()

    async def retrieve(self, query: str, user_id: str, use_reranking: bool = True, limit: int = 5) -> str:
        # 1. Rewrite query
        rewritten = await asyncio.to_thread(rewrite_query, query)
        
        # 2. Retrieve
        results = await self.retriever.retrieve(rewritten, limit=limit*2)
        
        # 3. Rerank
        if use_reranking:
            results = await self.reranker.rerank(query, results, top_k=limit)
        else:
            results = results[:limit]
            
        # 4. Build context
        context = self.builder.build_context(results, "", "", max_tokens=1500)
        return context
