import os
import logging
from bot import DocBot

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    # Get the token from environment variables
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("Discord token not found in environment variables!")
        return

    # Debug token format without exposing sensitive data
    token = token.strip()  # Remove any whitespace
    logger.debug(f"Token length: {len(token)}")
    logger.debug(f"Token format check - starts with: {token[:4]}... (rest hidden)")
    logger.debug(f"Token format check - ends with: ...{token[-4:]}") #Added this line for more robust check

    # Initialize and run the bot
    try:
        bot = DocBot()
        logger.info("Starting bot...")
        bot.run(token)  # Token is already stripped
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()