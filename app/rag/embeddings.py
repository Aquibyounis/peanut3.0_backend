"""
Peanut 3.0 - Local Offline Vector Embeddings
Uses fastembed to generate 768-dimension nomic-embed-text vectors.
"""

from fastembed import TextEmbedding
from app.core.config import EMBED_MODEL
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

# Initialize local embedding model on startup
try:
    logger.info("Initializing local fastembed model...", model=EMBED_MODEL)
    embedding_model = TextEmbedding(model_name=EMBED_MODEL)
    logger.info("Local fastembed model loaded successfully", model=EMBED_MODEL)
except Exception as e:
    logger.error("Failed to initialize fastembed model on startup", error=str(e))
    embedding_model = None


def generate_embedding(text: str):
    """Generate 768-dimension vector embedding offline using fastembed."""
    if not embedding_model:
        logger.error("Embedding model not loaded, cannot generate embedding.")
        return None
        
    try:
        # fastembed takes a list of strings, returns a generator
        embeddings = list(embedding_model.embed([text]))
        if embeddings:
            # Convert numpy array to standard Python list
            return embeddings[0].tolist()
    except Exception as e:
        logger.error("Local embedding generation failed", error=str(e))
        
    return None