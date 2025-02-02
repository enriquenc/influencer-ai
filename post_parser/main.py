import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from telethon.sync import TelegramClient
import os
from onchain_parser.monitor_service import monitor_service
import asyncio

from .bot.handlers import setup_handlers
from .config import load_config
from storage.storage import Storage
from .services.channel_service import ChannelService
from .services.parser_service import ParserService
from personality_analyzer import CharacterAnalyzer
from .services.log_service import LogService
from .services.wallet_service import WalletService

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_bot(config: dict, storage, analyzer: CharacterAnalyzer):
	"""Setup and run the bot with all dependencies"""

	# Initialize bot and dispatcher first
	bot = Bot(token=config["telegram"]["api_token"])
	dp = Dispatcher(storage=MemoryStorage())
	router = Router(name="main_router")
	dp.include_router(router)

	# Get the current event loop
	loop = asyncio.get_running_loop()

	# Initialize Telegram client
	telegram_client = TelegramClient(
		'session_name',  # Telethon will handle session file creation
		config["telegram"]["api_id"],
		config["telegram"]["api_hash"]
	)

	# Connect and handle authorization if needed
	if not telegram_client.is_connected():
		await telegram_client.connect()
		if not await telegram_client.is_user_authorized():
			logger.info("No session found. Please log in:")
			await telegram_client.start()
		logger.info("Telethon client connected successfully")

	# Initialize services
	channel_service = ChannelService(
		client=telegram_client,
		bot_token=config["telegram"]["api_token"]
	)
	parser_service = ParserService(telegram_client, DATA_DIR, config)
	log_service = LogService(SCRIPT_DIR)

	# Initialize wallet service with all required dependencies
	wallet_service = WalletService(
		bot=bot,
		storage=storage,
		personality_analyzer=analyzer,
		fsm_storage=dp.storage  # Pass the dispatcher's FSM storage
	)
	wallet_service._loop = loop  # Ensure the service has access to the main event loop

	# Start the monitor service background thread
	logger.info("Starting onchain monitor service...")
	monitor_service._start_monitor()
	logger.info("Onchain monitor service started successfully")

	# Restore existing wallet subscriptions from storage
	logger.info("Restoring wallet subscriptions...")
	channels = await storage.get_user_channels(None)  # Get all channels
	for channel in channels:
		if channel.wallets:
			for wallet in channel.wallets:
				if wallet_service.subscribe_wallet(wallet.address):
					logger.info(f"Restored subscription for wallet {wallet.address}")
				else:
					logger.warning(f"Failed to restore subscription for wallet {wallet.address}")

	# Setup handlers with all dependencies
	setup_handlers(
		router=router,
		channel_storage=storage,
		channel_service=channel_service,
		parser_service=parser_service,
		personality_analyzer=analyzer,
		log_service=log_service,
		wallet_service=wallet_service,
		config=config
	)

	# Start polling with allowed updates for callback queries
	await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

async def main() -> None:
	try:
		# Load configurations
		logger.info("Loading configurations...")
		telegram_config = load_config()
		analyzer_config = load_config()

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
		import asyncio
		logger.info("Starting Post Parser Bot...")
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		logger.info("Stopping monitor service...")
		monitor_service._stop_monitor()
		logger.info("Bot stopped!")