from fastapi import APIRouter
from datetime import datetime
from app.core.redis.client import redis_client
from app.core.postgres.database import engine
from app.core.qstash.producer import qstash_producer
from app.rag.qdrant_client import client as qdrant_client
from sqlalchemy import text
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def health_basic():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.get("/detailed")
async def health_detailed():
    status = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "services": {}}
    
    # Check DB (Neon PostgreSQL)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["services"]["postgres"] = "connected"
    except Exception:
        status["services"]["postgres"] = "disconnected"
        status["status"] = "degraded"
        
    # Check Redis (Upstash)
    try:
        if redis_client._client and await redis_client._client.ping():
            status["services"]["redis"] = "connected"
        else:
            status["services"]["redis"] = "disconnected"
            status["status"] = "degraded"
    except Exception:
        status["services"]["redis"] = "disconnected"
        status["status"] = "degraded"
        
    # Check Qdrant (Qdrant Cloud)
    try:
        qdrant_client.get_collections()
        status["services"]["qdrant"] = "connected"
    except Exception:
        status["services"]["qdrant"] = "disconnected"
        status["status"] = "degraded"
        
    # Check Groq
    try:
        import httpx
        from app.core.config import settings
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                timeout=5.0
            )
            if resp.status_code == 200:
                status["services"]["groq"] = "connected"
            else:
                status["services"]["groq"] = f"disconnected (HTTP {resp.status_code})"
                status["status"] = "degraded"
    except Exception:
        status["services"]["groq"] = "disconnected"
        status["status"] = "degraded"

    # Check QStash
    status["services"]["qstash"] = "connected" if qstash_producer._started else "disconnected"
    if not qstash_producer._started:
        status["status"] = "degraded"

    return status
