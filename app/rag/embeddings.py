"""
Peanut 3.0 - Embedding utility

Provides a single function `generate_embedding(text: str)` that returns a list[float]
or None. The implementation chooses between a local FastEmbed model and a remote
HuggingFace or Groq Inference endpoint based on environment variables.

- Remote mode is enabled by setting `USE_REMOTE_EMBED=1`.
- Provider is selected via `REMOTE_EMBED_PROVIDER` ("hf" or "groq").
- HF: `HF_TOKEN` + `HF_EMBED_ENDPOINT`.
- Groq: `GROQ_API_KEY` (uses Groq embedding endpoint).
"""
import requests
from app.core.logging.logger import get_logger
from app.core.config import settings, EMBED_MODEL

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# Remote HuggingFace embedding helper
# ----------------------------------------------------------------------
def _groq_remote_embedding(text: str) -> list[float] | None:
    # Groq uses the OpenAI-compatible API for embeddings.
    api_key = settings.groq_api_key
    model = getattr(settings, "groq_embed_model", "embed-3.5")
    if not api_key:
        logger.error("Groq API key not configured for remote embedding")
        return None
    try:
        import json
        endpoint = "https://api.groq.com/openai/v1/embeddings"
        payload = {"model": model, "input": [text]}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Expected response: {"data": [{"embedding": [...] }], ...}
        if "data" in data and data["data"]:
            return data["data"][0]["embedding"]
        logger.error("Groq response missing data field")
    except Exception as e:
        logger.error("Remote Groq embedding failed", error=str(e))
    return None

# ----------------------------------------------------------------------
# Remote Groq embedding helper
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Remote OpenAI embedding helper
# ----------------------------------------------------------------------
def _openai_remote_embedding(text: str) -> list[float] | None:
    api_key = settings.openai_api_key
    model_name = settings.remote_embed_model or "text-embedding-3-small"
    if not api_key:
        logger.error("OpenAI API key not configured for remote embedding")
        return None
    try:
        endpoint = "https://api.openai.com/v1/embeddings"
        payload = {"model": model_name, "input": [text]}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and data["data"]:
            return data["data"][0]["embedding"]
        logger.error("OpenAI response missing data field")
    except Exception as e:
        logger.error("Remote OpenAI embedding failed", error=str(e))
    return None

# ----------------------------------------------------------------------
# Local FastEmbed fallback (only imported if needed)
# ----------------------------------------------------------------------
embedding_model = None
if not settings.use_remote_embed:
    try:
        from fastembed import TextEmbedding
        logger.info("Initializing local fastembed model...", model=EMBED_MODEL)
        embedding_model = TextEmbedding(model_name=EMBED_MODEL)
        logger.info("Local fastembed model loaded successfully", model=EMBED_MODEL)
    except Exception as e:
        logger.error("Failed to initialize fastembed model on startup", error=str(e))
        embedding_model = None

def generate_embedding(text: str) -> list[float] | None:
    """Return a vector embedding for *text*.

    Uses the remote endpoint when `USE_REMOTE_EMBED` is true; otherwise falls
    back to the locally‑loaded FastEmbed model.
    """
    if settings.use_remote_embed:
        provider = settings.remote_embed_provider.lower()
        if provider == "hf":
            return _hf_remote_embedding(text)
        elif provider == "groq":
            return _groq_remote_embedding(text)
        else:
            logger.error(f"Unsupported remote embed provider: {provider}")
            return None

    if not embedding_model:
        logger.error("Embedding model not loaded, cannot generate embedding.")
        return None
    try:
        embeddings = list(embedding_model.embed([text]))
        if embeddings:
            return embeddings[0].tolist()
    except Exception as e:
        logger.error("Local embedding generation failed", error=str(e))
    return None