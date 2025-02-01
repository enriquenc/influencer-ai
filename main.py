import asyncio
import logging
from pathlib import Path
from post_parser.main import setup_bot
from personality_analyzer import CharacterAnalyzer
from storage.storage import Storage
from post_parser.config import load_config as load_telegram_config
from personality_analyzer.config import load_config as load_analyzer_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Load configurations
        logger.info("Loading configurations...")
        telegram_config = load_telegram_config()
        analyzer_config = load_analyzer_config()

        # Initialize storage
        logger.info("Initializing storage...")
        storage = Storage()

        # Initialize personality analyzer
        logger.info("Initializing personality analyzer...")
        analyzer = CharacterAnalyzer(
            api_key=analyzer_config["openai"]["api_key"],
            model=analyzer_config["openai"]["model"],
            temperature=analyzer_config["openai"]["temperature"]
        )

        # Setup and run bot
        logger.info("Starting bot...")
        await setup_bot(telegram_config, storage, analyzer)

    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped!")