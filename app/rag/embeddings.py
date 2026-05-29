"""
Peanut 3.0 - Embedding utility

Provides a single function `generate_embedding(text: str)` that returns a list[float]
or None. The implementation uses a remote HuggingFace or Groq Inference endpoint 
based on environment variables.

- Remote mode is enabled by setting `USE_REMOTE_EMBED=1`.
- Provider is selected via `REMOTE_EMBED_PROVIDER` ("hf" or "groq").
- HF: `HF_TOKEN` + `HF_EMBED_ENDPOINT`.
- Groq: `GROQ_API_KEY` (uses Groq embedding endpoint).
"""
import requests
from app.core.logging.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# Remote Groq embedding helper
# ----------------------------------------------------------------------
def _groq_remote_embedding(text: str) -> list[float] | None:
    # Groq uses the OpenAI-compatible API for embeddings.
    api_key = settings.groq_api_key
    model = getattr(settings, "groq_embed_model", "embed-3.5")
    if not api_key:
        logger.error("Groq API key not configured for remote embedding")
        return None
    try:
        endpoint = "https://api.groq.com/openai/v1/embeddings"
        payload = {"model": model, "input": [text]}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and data["data"]:
            return data["data"][0]["embedding"]
        logger.error("Groq response missing data field")
    except Exception as e:
        logger.error("Remote Groq embedding failed", error=str(e))
    return None

# ----------------------------------------------------------------------
# Remote OpenAI embedding helper (Fallback)
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
# Remote HF embedding helper (Fallback)
# ----------------------------------------------------------------------
def _hf_remote_embedding(text: str) -> list[float] | None:
    api_key = settings.hf_token
    endpoint = settings.hf_embed_endpoint
    if not api_key or not endpoint:
        logger.error("HF token or endpoint not configured for remote embedding")
        return None
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"inputs": text}
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return data
        logger.error("HF embedding response format unexpected")
    except Exception as e:
        logger.error("Remote HF embedding failed", error=str(e))
    return None

def generate_embedding(text: str) -> list[float] | None:
    """Return a vector embedding for *text*.

    Uses the remote endpoint specified by the environment variables.
    """
    if settings.use_remote_embed:
        provider = settings.remote_embed_provider.lower()
        if provider == "hf":
            return _hf_remote_embedding(text)
        elif provider == "groq":
            return _groq_remote_embedding(text)
        elif provider == "openai":
            return _openai_remote_embedding(text)
        else:
            logger.error(f"Unsupported remote embed provider: {provider}")
            return None

    logger.error("Local embeddings are disabled to save memory. Please use USE_REMOTE_EMBED=1.")
    return None