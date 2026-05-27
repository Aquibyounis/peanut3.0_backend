from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.keyword_retriever import KeywordRetriever

class HybridRetriever:
    def __init__(self):
        self.vector_retriever = VectorRetriever()
        self.keyword_retriever = KeywordRetriever()

    async def retrieve(self, query: str, limit: int = 5, vector_weight: float = 0.7, keyword_weight: float = 0.3) -> list[dict]:
        vector_results = await self.vector_retriever.retrieve(query, limit=limit*2)
        keyword_results = await self.keyword_retriever.retrieve(query, limit=limit*2)
        
        return self._reciprocal_rank_fusion(vector_results, keyword_results, limit)
        
    def _reciprocal_rank_fusion(self, vector_results: list[dict], keyword_results: list[dict], limit: int, k: int = 60) -> list[dict]:
        rrf_scores = {}
        result_map = {}
        
        for rank, res in enumerate(vector_results):
            text = res["text"]
            if text not in rrf_scores:
                rrf_scores[text] = 0
                result_map[text] = res
            rrf_scores[text] += 1 / (k + rank + 1)
            
        for rank, res in enumerate(keyword_results):
            text = res["text"]
            if text not in rrf_scores:
                rrf_scores[text] = 0
                result_map[text] = res
            rrf_scores[text] += 1 / (k + rank + 1)
            
        sorted_texts = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        final_results = []
        for text in sorted_texts[:limit]:
            res = result_map[text]
            res["score"] = rrf_scores[text]
            final_results.append(res)
            
        return final_results
