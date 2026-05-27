"""
Peanut 3.0 - Semantic Query Rewriter
Uses Groq API synchronously via the fast gemma2-9b-it model.
"""

from app.llm.llm_service import llm_service
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


def rewrite_query(query: str) -> str:
    """Rewrite query to optimize for semantic search."""
    prompt = f"""
    Rewrite this user query into an optimized semantic search query.
    Expand related concepts naturally.
    Keep response concise.

    User Query:
    {query}
    """
    
    try:
        logger.info("Rewriting user query via Groq (llama-3.1-8b-instant)")
        response = llm_service.groq_provider.generate_sync(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",  # Use lightweight fast chat model
            temperature=0.1,
            max_tokens=60
        )
        rewritten = response.strip()
        logger.info("Query rewritten successfully", original=query, rewritten=rewritten)
        return rewritten
    except Exception as e:
        logger.error("Query rewriter failed, returning original query", error=str(e))
        return query