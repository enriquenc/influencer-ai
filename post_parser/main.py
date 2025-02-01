import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, CommandObject
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import json
import os
from datetime import datetime
from .singletone import MongoDBSingleton
from .config import load_config
from .storage import Storage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

logging.basicConfig(level=logging.INFO)

# Load configuration
config = load_config()

# Initialize both storages
channel_storage = Storage()  # Our custom storage for channels and wallets
fsm_storage = MemoryStorage()  # FSM storage for dialog states

# Initialize the aiogram Bot and Dispatcher with proper startup
bot = Bot(token=config["telegram"]["api_token"])
# Create dispatcher with FSM storage
dp = Dispatcher(storage=fsm_storage)

mongo_uri = config["mongo"]["uri"]
db_name = config["mongo"]["db_name"]
mongo_singleton = MongoDBSingleton(mongo_uri, db_name)

# Create and configure router
router = Router(name="main_router")
dp.include_router(router)  # Register router immediately after creation

# Initialize the Telethon client
telegram_client = None  # Initialize as None first

async def init_telegram_client():
	global telegram_client
	if telegram_client is None:
		telegram_client = TelegramClient(
			'session_name',
			config["telegram"]["api_id"],
			config["telegram"]["api_hash"]
		)
		if not telegram_client.is_connected():
			await telegram_client.connect()
			logging.info("Telethon client connected")

class AIPersonality:
	"""AI Influencer personality traits and responses"""

	WELCOME_MESSAGE = """
Hey there! 👋 I'm your AI Influencer Assistant, and I'm here to help you analyze and optimize your social media presence!

Here's what I can do for you:
📊 Parse and analyze your Telegram channel posts
💼 Track wallets associated with your channels
📈 Provide insights about your content

Commands:
/add_channel - Add a Telegram channel
/add_wallet - Link a wallet to your channel
/list_channels - Show your channels
/list_wallets - Show channel's wallets
/parse - Analyze channel's posts

Let's make your social media presence amazing! 🚀
	"""

	@staticmethod
	def channel_added(channel_name: str) -> str:
		# Remove @ if present for display
		display_name = channel_name[1:] if channel_name.startswith('@') else channel_name
		return f"""
Awesome! 🎉 I've added {display_name} to your collection.
You can now:
• Add wallets with /add_wallet
• Analyze posts with /parse
• View channel details with /list_wallets

Ready to dive deeper into your channel's analytics? 📊
	"""

	@staticmethod
	def wallet_added(channel_name: str, wallet: str) -> str:
		# Remove @ if present for display
		display_name = channel_name[1:] if channel_name.startswith('@') else channel_name
		return f"""
Great! 💼 New wallet linked to {display_name}:
`{wallet}`

I'll keep track of this wallet's activities for you. You can view all linked wallets using:
/list_wallets

Want to analyze your channel's posts? Try:
/parse
	"""

# Add this class to define states
class AddChannel(StatesGroup):
	waiting_for_channel = State()

# Command handlers
@router.message(Command("start"))
async def cmd_start(message: types.Message):
	await message.answer(AIPersonality.WELCOME_MESSAGE)
	try:
		await mongo_singleton.add_user(str(message.from_user.id), "", [])
	except Exception as e:
		logging.error(f"Failed to add user: {e}")
		await message.answer("Failed to register user.")

@router.message(Command("add_channel"))
async def add_channel_start(message: types.Message, state: FSMContext):
	await message.reply("Please provide a channel username starting with @")
	await state.set_state(AddChannel.waiting_for_channel)
#	try:
#		await mongo_singleton.add_channel_to_user(str(message.from_user.id), str(message.text))
#	except Exception as e:
#		logging.error(f"Failed to add user: {e}")
#		await message.answer("Failed to register user.")

@router.message(AddChannel.waiting_for_channel)
async def add_channel_finish(message: types.Message, state: FSMContext):
	try:
		channel_username = message.text
		logging.info(f"Received channel username: {channel_username}")

		if not channel_username.startswith('@'):
			await message.reply("Channel username must start with @")
			return

		logging.info(f"Attempting to add channel: {channel_username}")

		# Ensure Telethon client is initialized
		await init_telegram_client()

		# Try to get channel info from Telegram
		try:
			channel = await telegram_client.get_entity(channel_username)
			logging.info(f"Channel info retrieved: {channel}")

			stored_channel = channel_storage.add_channel(
				user_id=message.from_user.id,
				username=channel_username[1:],
				title=channel.title
			)
			logging.info(f"Channel stored: {stored_channel}")

			await message.reply(AIPersonality.channel_added(channel_username))
			await state.clear()  # Clear the state after successful addition
		except ValueError as ve:
			await message.reply(f"Could not find channel {channel_username}. Please make sure the channel exists and is public.")
			logging.error(f"Channel not found: {ve}")
		except Exception as e:
			await message.reply(f"Error accessing channel: {str(e)}")
			logging.error(f"Error getting channel info: {e}", exc_info=True)

	except Exception as e:
		logging.error(f"Error adding channel: {str(e)}", exc_info=True)
		await message.reply(f"Sorry! 😅 I couldn't add that channel. Error: {str(e)}")
	finally:
		await state.clear()  # Always clear state even if there's an error

@router.message(Command("add_wallet"))
async def add_wallet(message: types.Message):
	command_parts = message.text.split()
	if len(command_parts) < 3:
		await message.reply("Please provide channel username and wallet address")
		return

	channel_username = command_parts[1]
	wallet_address = command_parts[2]

	wallet = channel_storage.add_wallet(channel_username, wallet_address)
	if wallet:
		await message.reply(AIPersonality.wallet_added(channel_username, wallet_address))
	else:
		await message.reply(f"Channel {channel_username} not found! Add it first with /add_channel {channel_username}")

@router.message(Command("list_channels"))
async def list_channels(message: types.Message):
	channels = channel_storage.get_user_channels(message.from_user.id)

	if not channels:
		await message.reply("You haven't added any channels yet! Use /add_channel to get started.")
		return

	response = "Your channels:\n\n"
	for channel in channels:
		response += f"📢 {channel.username}\n"
		response += f"Added: {channel.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
		response += f"Wallets: {len(channel.wallets)}\n\n"

	await message.reply(response)

@router.message(Command("list_wallets"))
async def list_wallets(message: types.Message):
	command_parts = message.text.split()
	if len(command_parts) < 2:
		await message.reply("Please provide a channel username")
		return

	channel_username = command_parts[1]
	wallets = channel_storage.get_channel_wallets(channel_username)

	# Remove @ if present for display
	display_name = channel_username[1:] if channel_username.startswith('@') else channel_username

	if not wallets:
		await message.reply(f"No wallets found for {display_name}! Add one with /add_wallet {display_name} wallet_address")
		return

	response = f"Wallets for {display_name}:\n\n"
	for wallet in wallets:
		response += f"💼 `{wallet.address}`\n"
		response += f"Chain: {wallet.chain}\n"
		response += f"Added: {wallet.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"

	await message.reply(response, parse_mode="Markdown")

@router.message(Command("parse"))
async def parse(message: types.Message):
	command_parts = message.text.split()
	if len(command_parts) < 2:
		await message.reply("Please provide a channel username")
		return

	channel_username = command_parts[1]
	# Remove @ if present for display
	display_name = channel_username[1:] if channel_username.startswith('@') else channel_username

	await message.reply(f"🔍 Analyzing posts from {display_name}...")

	try:
		messages = await telegram_client.get_messages(
			channel_username,
			limit=config.get("max_messages_per_parse", 1000)
		)

		parsed_messages = []
		for msg in messages[:-1]:
			if msg.text:
				parsed_messages.append(msg.text)

		os.makedirs(DATA_DIR, exist_ok=True)
		file_path = os.path.join(DATA_DIR, f"{display_name}_posts.json")

		with open(file_path, "w", encoding="utf-8") as json_file:
			json.dump(parsed_messages, json_file, ensure_ascii=False, indent=4)

		await message.answer(
			f"""✨ Analysis complete! I've processed {len(parsed_messages)} posts from {display_name}.

The data has been saved and I'm ready to provide insights about your content!
			"""
		)

	except Exception as e:
		await message.answer(f"Oops! 😅 Something went wrong: {str(e)}")

async def main() -> None:
	try:
		# Initialize and connect Telethon client
		logging.info("Starting Telethon client...")
		await init_telegram_client()

		# Start polling with all required setup
		logging.info("Starting bot polling...")

		# Start polling with all update types
		await dp.start_polling(
			bot,
			allowed_updates=["message"]
		)

	except Exception as e:
		logging.error(f"Error in main: {str(e)}", exc_info=True)
		raise

if __name__ == "__main__":
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
	)

	try:
		import asyncio
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		logging.info("Bot stopped!")
