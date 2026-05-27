"""
Peanut 3.0 - Resilient LLM Reranker
Uses Groq API asynchronously to compute zero-shot relevance scores.
"""

from app.llm.llm_service import llm_service
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class Reranker:
    async def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        """Rank retrieved passages by semantic relevance to the query using Groq."""
        if not results:
            return []
            
        passages = [res["text"][:500] for res in results]
        passages_text = "\n\n".join([f"[{i}] {text}" for i, text in enumerate(passages)])
        
        prompt = f"""Score the relevance of each passage to the query on a 0-10 scale.
Query: {query}
Passages:
{passages_text}
Output ONLY a comma-separated list of scores in order, e.g. 8,2,9,0,5"""

        try:
            logger.info("Reranking retrieved chunks via Groq (llama-3.1-8b-instant)")
            content = await llm_service.groq_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",  # Use fast model for low-latency reranking
                temperature=0.0,
                max_tokens=50
            )
            
            # Extract scores
            scores = [
                float(s.strip()) 
                for s in content.split(",") 
                if s.strip().replace('.', '', 1).isdigit()
            ]
            
            if len(scores) == len(results):
                for idx, res in enumerate(results):
                    res["score"] = scores[idx]
                
                sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
                logger.info("Reranking completed successfully", top_score=sorted_results[0]["score"] if sorted_results else 0)
                return sorted_results[:top_k]
                
        except Exception as e:
            logger.error("Reranking failed, falling back to vector score ordering", error=str(e))
            
        return results[:top_k]
