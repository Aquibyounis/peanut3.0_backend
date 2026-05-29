import discord
from discord.ext import commands
from app.core.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class PeanutSupportBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            await self.load_extension("app.discord.cogs.support_bridge")
            logger.info("Loaded support_bridge cog")
        except Exception as e:
            logger.error("Failed to load support_bridge cog", error=str(e))

    async def on_ready(self):
        logger.info(f"Discord Bot logged in as {self.user} (ID: {self.user.id})")

bot = PeanutSupportBot()
