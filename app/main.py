from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import existing router (preserved)
from app.api.chat import router as legacy_chat_router

# Import new routers
from app.api.routes.auth import router as auth_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.chat import router as chat_v2_router
from app.api.routes.memory import router as memory_router
from app.api.routes.connect import router as connect_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.admin import router as admin_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.support import router as support_router

# Import WebSocket router
from app.api.websocket.chat_ws import router as ws_router
from app.api.websocket.support_ws import router as ws_support_router

# Import middleware
from app.api.middleware.logging_middleware import RequestLoggingMiddleware
from app.api.middleware.error_handler import register_error_handlers
from app.api.middleware.auth_middleware import AuthMiddleware

# Import infrastructure
from app.core.redis.client import redis_client
from app.core.qstash.producer import qstash_producer
from app.core.postgres.database import engine
from app.core.logging.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Peanut 3.0", env=settings.app_env)
    
    # Connect Redis
    try:
        await redis_client.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis connection failed", error=str(e))
    
    # Start QStash producer
    try:
        await qstash_producer.start()
        logger.info("QStash producer started")
    except Exception as e:
        logger.warning("QStash connection failed", error=str(e))
        
    # Start Discord Bot
    discord_task = None
    if settings.discord_bot_token:
        from app.discord.bot import bot
        import asyncio
        discord_task = asyncio.create_task(bot.start(settings.discord_bot_token))
        logger.info("Discord bot started")
    else:
        logger.warning("DISCORD_BOT_TOKEN not set, Discord integration disabled")
    
    logger.info("Peanut 3.0 startup complete")
    yield
    
    # Shutdown
    logger.info("Shutting down Peanut 3.0")
    try:
        await redis_client.disconnect()
    except Exception:
        pass
    try:
        await qstash_producer.stop()
    except Exception:
        pass
    try:
        await engine.dispose()
    except Exception:
        pass
        
    if discord_task:
        discord_task.cancel()
        from app.discord.bot import bot
        await bot.close()
        
    logger.info("Peanut 3.0 shutdown complete")

app = FastAPI(
    title="Peanut 3.0",
    description="Production AI Platform - Semantic AI Operating System",
    version="3.0.0",
    lifespan=lifespan
)

# CORS
origins = settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthMiddleware)

# Error handlers
register_error_handlers(app)

# Legacy router (preserved)
app.include_router(legacy_chat_router)

# New routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
app.include_router(chat_v2_router, prefix="/v2", tags=["Chat V2"])
app.include_router(memory_router, prefix="/memory", tags=["Memory"])
app.include_router(connect_router, tags=["Connect"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(support_router, prefix="/support", tags=["Support"])
app.include_router(ws_router, tags=["WebSocket"])
app.include_router(ws_support_router, tags=["Support WebSocket"])

@app.get("/")
async def root():
    return {
        "message": "Peanut Backend Running",
        "version": "3.0.0",
        "status": "operational"
    }