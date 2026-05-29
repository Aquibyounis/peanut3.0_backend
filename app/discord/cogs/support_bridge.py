import asyncio
import discord
from discord.ext import commands
from app.core.logging.logger import get_logger
from app.core.redis.pubsub import subscribe_channel
from app.core.postgres.database import AsyncSessionLocal
from app.services.support import SupportService

logger = get_logger(__name__)

class SupportBridgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.listen_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.listen_task:
            self.listen_task = self.bot.loop.create_task(self.listen_to_redis())

    async def listen_to_redis(self):
        logger.info("Discord bot starting to listen to redis for support messages")
        async for message in subscribe_channel("support:discord_outbound"):
            try:
                event = message.get("event")
                if event == "user_message":
                    session_id = message["session_id"]
                    thread_id = message.get("thread_id")
                    content = message["content"]
                    await self.handle_outbound_message(session_id, thread_id, content)
            except Exception as e:
                logger.error("Error processing outbound discord message", error=str(e))

    async def handle_outbound_message(self, session_id: str, thread_id: str, content: str):
        from app.core.config import settings
        if not settings.discord_guild_id or not settings.discord_support_channel_id:
            logger.warning("Discord guild/channel ID not configured")
            return
            
        guild = self.bot.get_guild(int(settings.discord_guild_id))
        if not guild:
            try:
                guild = await self.bot.fetch_guild(int(settings.discord_guild_id))
            except Exception as e:
                logger.error("Guild not found", error=str(e))
                return
            
        support_channel = guild.get_channel(int(settings.discord_support_channel_id))
        if not support_channel:
            try:
                support_channel = await guild.fetch_channel(int(settings.discord_support_channel_id))
            except Exception as e:
                logger.error("Support channel not found or invalid", error=str(e))
                return

        thread = None
        if thread_id:
            try:
                thread = await guild.fetch_channel(int(thread_id))
            except:
                thread = None
                
        if not thread:
            # Create thread
            message = await support_channel.send(f"New support session: {session_id}")
            thread = await support_channel.create_thread(name=f"session-{session_id[-6:]}", message=message)
            
            # Update DB with thread_id
            async with AsyncSessionLocal() as db:
                service = SupportService(db)
                from uuid import UUID
                await service.repo.update_session_thread(UUID(session_id), str(thread.id))

        await thread.send(f"**User**: {content}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if message is in a thread
        if isinstance(message.channel, discord.Thread):
            # Check if this thread belongs to our support channel
            from app.core.config import settings
            if str(message.channel.parent_id) == settings.discord_support_channel_id:
                # Handle reply
                async with AsyncSessionLocal() as db:
                    service = SupportService(db)
                    await service.handle_discord_reply(str(message.channel.id), message.content)

async def setup(bot):
    await bot.add_cog(SupportBridgeCog(bot))
