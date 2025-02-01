import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import json
from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient
from .config import load_config

load_dotenv()

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

logging.basicConfig(level=logging.INFO)

# Constants
USER_COLLECTION = "users"
CHANNEL_COLLECTION = "channels"

# Load configuration
config = load_config()

# Environment variables
API_TOKEN = os.getenv("API_TOKEN")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

# MongoDB setup

# Initialize the aiogram Bot
bot = Bot(token=config["telegram"]["api_token"])
dp = Dispatcher()
router = Router()

# Initialize the Telethon client
telegram_client = TelegramClient(
	'session_name',
	config["telegram"]["api_id"],
	config["telegram"]["api_hash"]
)

async def get_user_default_data(user_id: int) -> dict:
	return {
		"user_id": user_id,
		"channels": []
	}



# Command to start the bot
@router.message(Command("start"))
async def cmd_start(message: types.Message):
	await message.answer("""Hello! I'm an AI influencer. I can help you write posts for your Telegram channel.
						Send /parse followed by a channel username to parse posts.
						Don't forget to add me as admin to the channel.""")



# Command to add a channel
@router.message(Command("add_channel"))
async def add_channel(message: types.Message):
	command_parts = message.text.split(" ")
	if len(command_parts) < 2:
		await message.reply("Please provide a channel username! Example: /add_channel @example_channel")
		return

	channel_username = command_parts[1]

	await message.reply(f"Channel {channel_username} has been added to your list")

# Command to parse posts from a channel
@router.message(Command("parse"))
async def parse(message: types.Message):
	await message.reply("Parsing posts...")

	channel_usernames = ["@u_now"]


	for channel_username in channel_usernames:
		try:
			messages = await telegram_client.get_messages(
				channel_username,
				limit=config.get("max_messages_per_parse", 1000)
			)

			# Prepare a list to store the messages
			parsed_messages = []

			for msg in messages[:-1]:
				if msg.text:  # Ensure the message has text content
					parsed_messages.append(msg.text)

			# Create data directory if it doesn't exist
			os.makedirs(DATA_DIR, exist_ok=True)

			# Save the parsed messages to a JSON file
			file_path = os.path.join(DATA_DIR, f"{channel_username[1:]}_posts.json")
			with open(file_path, "w", encoding="utf-8") as json_file:
				json.dump(parsed_messages, json_file, ensure_ascii=False, indent=4)

			await message.answer(f"Posts are parsed and saved to '{file_path}'")

		except Exception as e:
			await message.answer(f"Error: {str(e)}")

# Register the router in aiogram's dispatcher
dp.include_router(router)

async def main() -> None:
	await telegram_client.start()
	await dp.start_polling(bot)

# Start the aiogram polling loop
if __name__ == "__main__":
	import asyncio
	asyncio.run(main())