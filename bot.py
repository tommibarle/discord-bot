import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class DocBot(commands.Bot):
    def __init__(self):
        # Enable all intents that we need
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.messages = True  # Enable messages intent
        intents.guild_messages = True  # Enable guild messages intent
        intents.members = True  # Enable members intent for server member info

        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/documents"
            )
        )

    async def setup_hook(self):
        # Load the document handler cog
        await self.load_extension("cogs.document_handler")
        logger.info("Document handler cog loaded")

    async def on_ready(self):
        logger.info(f"Bot is ready! Logged in as {self.user}")

        # Sync commands with Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_error(self, event_method: str, *args, **kwargs):
        logger.error(f"Error in {event_method}: ", exc_info=True)