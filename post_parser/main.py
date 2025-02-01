import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, CommandObject
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import json
import os
from datetime import datetime
from .config import load_config
from .storage import Storage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon.tl.types import Channel

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

admin_id = 344996628

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

	"""

# Add this class to define states
class AddChannel(StatesGroup):
	waiting_for_channel = State()

class AddWallet(StatesGroup):
	waiting_for_wallet = State()

class WalletList(StatesGroup):
	waiting_for_wallet_list = State()


async def cleanup_username(username: str) -> str:
	"""
	Remove @ if present for display
	"""
	if username.startswith('@'):
		return username
	else:
		return '@' + username.split('/')[-1]

async def check_admin_rights(channel_entity, message: types.Message) -> bool:
	"""
	Check if the bot is an administrator of the channel.
	Returns True if bot is admin, False otherwise.
	"""

	ADMIN_RIGHTS_REQUEST = """
	Please add the bot as an administrator to the channel with these permissions:
								✓ Send Messages
								✓ Edit Messages
								✓ Delete Messages
								✓ Post Messages"""
	try:
		while True:
			try:
				permission = await telegram_client.get_permissions(channel_entity, admin_id)
				if permission.is_admin:
					return True
				else:
					await message.answer(ADMIN_RIGHTS_REQUEST)
					return False
			except Exception as e:
				await message.answer(ADMIN_RIGHTS_REQUEST)
				return False
	except Exception as e:
		logging.error(f"Error checking admin rights: {e}")
		return False

# Command handlers
@router.message(Command("start"))
async def cmd_start(message: types.Message):
	await message.answer(AIPersonality.WELCOME_MESSAGE)

@router.message(Command("add_channel"))
async def add_channel_start(message: types.Message, state: FSMContext):
	await message.reply("Please provide a channel username starting with @ or link to it")
	await state.set_state(AddChannel.waiting_for_channel)

@router.message(AddChannel.waiting_for_channel)
async def add_channel_finish(message: types.Message, state: FSMContext):
	try:
		channel_username = message.text
		logging.info(f"Received channel username: {channel_username}")

		# Format check and conversion
		if channel_username.startswith('https://t.me/'):
			channel_username = await cleanup_username(channel_username)
		elif not channel_username.startswith('@'):
			await message.reply("Please provide a valid channel username starting with @ or a t.me link")
			return

		await init_telegram_client()

		try:
			channel = await telegram_client.get_entity(channel_username)
			if not isinstance(channel, Channel):
				await message.reply("Send me valid telegram tag or link")
				return
			logging.info(f"Channel info retrieved: {channel}")

			# Store channel information
			stored_channel = channel_storage.add_channel(
				user_id=message.from_user.id,
				username=channel_username[1:],
				title=channel.title
			)
			logging.info(f"Channel stored: {stored_channel}")

			await message.reply(AIPersonality.channel_added(channel_username))

			await state.clear()
			return await parse(message, channel_username)


		except ValueError as ve:
			await message.reply(
				f"Could not find channel {channel_username}.\n"
				"Please make sure:\n"
				"1. The channel exists\n"
				"2. The channel is public\n"
				"3. You provided the correct username/link"
			)
			logging.error(f"Channel not found: {ve}")
		except Exception as e:
			await message.reply(f"Error accessing channel: {str(e)}")
			logging.error(f"Error getting channel info: {e}", exc_info=True)

	except Exception as e:
		logging.error(f"Error adding channel: {str(e)}", exc_info=True)
		await message.reply(f"Sorry! 😅 I couldn't add that channel. Error: {str(e)}")
	await state.clear()

@router.message(Command("add_wallet"))
async def add_wallet(message: types.Message, state: FSMContext):
	await message.reply("Please provide a channel username and wallet address")
	await state.set_state(AddWallet.waiting_for_wallet)


@router.message(AddWallet.waiting_for_wallet)
async def add_wallet_finish(message: types.Message, state: FSMContext):
	command_parts = message.text.split()
	if len(command_parts) < 2:
		await message.answer("Please provide channel username and wallet address")
		return

	channel_username = await cleanup_username(command_parts[0])
	wallet_address = command_parts[1]

	wallet = channel_storage.add_wallet(channel_username, wallet_address)
	if wallet:
		await message.reply(AIPersonality.wallet_added(channel_username, wallet_address))
	else:
		await message.reply(f"Channel {channel_username} not found! Add it first with /add_channel {channel_username}")
	
	await state.clear()


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

	await message.answer(response)

@router.message(Command("list_wallets"))
async def list_wallets(message: types.Message, state: FSMContext):
	await message.reply("Please provide a channel username")
	await state.set_state(WalletList.waiting_for_wallet_list)

@router.message(WalletList.waiting_for_wallet_list)
async def list_wallets_finish(message: types.Message, state: FSMContext):
	channel_username = await cleanup_username(message.text)
	
	wallets = channel_storage.get_channel_wallets(channel_username)

	display_name = channel_username[1:] if channel_username.startswith('@') else channel_username

	if not wallets:
		await message.reply(f"No wallets found for {display_name}! Add one with /add_wallet {display_name} wallet_address")
		return
	

	response = f"Wallets for {display_name}:\n\n"
	for wallet in wallets:
		response += f"💼 {wallet.address}\n"
		response += f"Chain: {wallet.chain}\n"
		response += f"Added: {wallet.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
	print(f"Response: {response}")

	await message.answer(response)
	await state.clear()

async def parse(message: types.Message, display_name: str):

	print(f"🔍 Analyzing posts from {display_name}...")

	try:
		messages = await telegram_client.get_messages(
			display_name,
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

		print(
			f"""✨ Analysis complete! I've processed {len(parsed_messages)} posts from {display_name}.

The data has been saved and I'm ready to provide insights about your content!
			"""
		)

		### Make personality analysis and write this to db
		###
		###

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