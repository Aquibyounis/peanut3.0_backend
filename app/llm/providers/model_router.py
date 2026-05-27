"""
Peanut 3.0 - Intelligent Model Router
Routes prompts to optimized models based on intent/task type.
"""

from app.core.logging.logger import get_logger

logger = get_logger(__name__)

# Specialized routing map
ROUTING_MAP = {

    # Ultra-fast lightweight chat
    "fast_chat": "llama-3.1-8b-instant",

    # Heavy reasoning + architecture understanding
    "reasoning": "deepseek-r1-distill-llama-70b",

    # Main RAG production model
    "general_rag": "llama-3.3-70b-versatile",

    # Stable fallback model
    "fallback": "llama-3.1-8b-instant"
}

class ModelRouter:
    def route_for_query(self, query: str) -> str:
        """Route user query dynamically based on complexity or explicit keywords."""
        query_lower = query.lower()
        
        # Check for deep reasoning keywords
        if any(kw in query_lower for kw in ["why", "explain", "compare", "analyze", "deeply", "reason"]):
            logger.info("Routing query to Reasoning model", query=query[:30])
            return ROUTING_MAP["reasoning"]
            
        # Check for short, casual chat keywords
        if len(query.split()) < 4 or any(kw in query_lower for kw in ["hi", "hello", "hey", "ping", "test"]):
            logger.info("Routing query to Fast Chat model", query=query[:30])
            return ROUTING_MAP["fast_chat"]
            
        # Default RAG queries
        logger.info("Routing query to General RAG model", query=query[:30])
        return ROUTING_MAP["general_rag"]
        
    def get_model_for_task(self, task: str) -> str:
        """Get model by category name."""
        return ROUTING_MAP.get(task, ROUTING_MAP["general_rag"])
