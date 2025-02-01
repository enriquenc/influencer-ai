import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from telethon.sync import TelegramClient
import os

from .bot.handlers import setup_handlers
from .config import load_config
from .storage.storage import Storage
from .services.channel_service import ChannelService
from .services.parser_service import ParserService
from personality_analyzer import CharacterAnalyzer
from .services.log_service import LogService

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
logger.info("Loading configuration...")
config = load_config()
logger.info("Configuration loaded successfully")

# Initialize storages
channel_storage = Storage()
fsm_storage = MemoryStorage()

# Initialize the bot and dispatcher
logger.info("Initializing bot...")
bot = Bot(token=config["telegram"]["api_token"])
dp = Dispatcher(storage=fsm_storage)
router = Router(name="main_router")
dp.include_router(router)
logger.info("Bot initialized successfully")

# Initialize Telethon client
telegram_client = None

async def init_telegram_client():
	global telegram_client
	if telegram_client is None:
		logger.info("Connecting to Telegram client...")
		telegram_client = TelegramClient(
			'session_name',
			config["telegram"]["api_id"],
			config["telegram"]["api_hash"]
		)
		if not telegram_client.is_connected():
			await telegram_client.connect()
			logger.info("Telethon client connected successfully")

async def setup_bot(config: dict, storage, analyzer: CharacterAnalyzer):
	"""Setup and run the bot with all dependencies"""

	# Initialize Telegram client
	telegram_client = TelegramClient(
		'session_name',
		config["telegram"]["api_id"],
		config["telegram"]["api_hash"]
	)

	if not telegram_client.is_connected():
		await telegram_client.connect()
		logger.info("Telethon client connected successfully")

	# Initialize services
	channel_service = ChannelService(telegram_client)
	parser_service = ParserService(telegram_client, DATA_DIR, config)
	log_service = LogService(SCRIPT_DIR)

	# Initialize bot and dispatcher
	bot = Bot(token=config["telegram"]["api_token"])
	dp = Dispatcher(storage=MemoryStorage())

	# Create and include router
	router = Router(name="main_router")
	dp.include_router(router)

	# Setup handlers with all dependencies
	setup_handlers(
		router=router,
		channel_storage=storage,
		channel_service=channel_service,
		parser_service=parser_service,
		personality_analyzer=analyzer,
		log_service=log_service,
		config=config
	)

	# Start polling with allowed updates for callback queries
	await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

async def main() -> None:
	try:
		# Initialize services
		logger.info("Initializing services...")
		await init_telegram_client()
		channel_service = ChannelService(telegram_client)
		parser_service = ParserService(telegram_client, DATA_DIR, config)

		# Setup handlers
		logger.info("Setting up command handlers...")
		setup_handlers(
			router=router,
			channel_storage=channel_storage,
			channel_service=channel_service,
			parser_service=parser_service
		)
		logger.info("Command handlers set up successfully")

		# Start polling
		logger.info("Starting bot polling...")
		await dp.start_polling(bot, allowed_updates=["message"])

	except Exception as e:
		logger.error(f"Error in main: {str(e)}", exc_info=True)
		raise

if __name__ == "__main__":
	try:
		import asyncio
		logger.info("Starting Post Parser Bot...")
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		logger.info("Bot stopped!")