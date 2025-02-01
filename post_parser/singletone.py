import logging
import motor.motor_asyncio

class Singleton:
	_instances = {}

	def __new__(cls, *args, **kwargs):
		if cls not in cls._instances:
			instance = super().__new__(cls)
			cls._instances[cls] = instance
			instance.__initialized = False
		return cls._instances[cls]

class MongoDBSingleton(Singleton):
	def __init__(self, mongo_uri, db_name):
		if not hasattr(self, 'db'):
			db_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
			self.db = db_client[db_name]
			logging.basicConfig(level=logging.INFO)
			self.logger = logging.getLogger(__name__)

	async def get_collection(self, collection_name):
		try:
			return self.db[collection_name]
		except Exception as e:
			self.logger.error(f"Failed to get collection: {e}")
			raise

	async def insert_message(self, collection, message):
		try:
			result = await collection.insert_one(message)
			return result.inserted_id
		except Exception as e:
			self.logger.error(f"Failed to insert message: {e}")
			raise

	async def add_user(self, user_id, wallet_id, channel_list):
		collection = await self.get_collection('users')
		user_data = {
			"telegram_id": user_id,
			"wallet_id": wallet_id,
			"channel_list_ids": channel_list
		}
		return await self.insert_message(collection, user_data)

	async def get_all_users(self):
		collection = await self.get_collection('users')
		cursor = collection.find({})
		return [document async for document in cursor]

	async def add_channel(self, channel_id, personality):
		collection = await self.get_collection('channels')
		channel_data = {
			"channel_id": channel_id,
			"personality": personality
		}
		return await self.insert_message(collection, channel_data)

	async def get_all_channels(self):
		collection = await self.get_collection('channels')
		cursor = collection.find({})
		return [document async for document in cursor]

	async def add_channel_to_user(self, telegram_id, new_channel_id):
		collection = await self.get_collection('users')
		try:
			user = await collection.find_one({"telegram_id": telegram_id})
			if not user:
				self.logger.error(f"User with telegram_id {telegram_id} not found")
				return None

			if "channel_list_ids" not in user:
				user["channel_list_ids"] = []
			if new_channel_id not in user["channel_list_ids"]:
				user["channel_list_ids"].append(new_channel_id)

			result = await collection.update_one(
				{"telegram_id": telegram_id},
				{"$set": {"channel_list_ids": user["channel_list_ids"]}}
			)
			if result.modified_count > 0:
				self.logger.info(f"Added channel {new_channel_id} to user {telegram_id}")
				return True
			else:
				self.logger.error(f"Failed to update user {telegram_id}")
				return False
		except Exception as e:
			self.logger.error(f"Failed to add channel to user: {e}")
			raise

	async def update_channel_personality(self, channel_id, new_personality):
		collection = await self.get_collection('channels')
		try:
			result = await collection.update_one(
				{"channel_id": channel_id},
				{"$set": {"personality": new_personality}}
			)
			if result.modified_count > 0:
				self.logger.info(f"Updated personality for channel {channel_id} to {new_personality}")
				return True
			else:
				if result.matched_count == 0:
					self.logger.error(f"Channel with id {channel_id} not found")
					return False
				self.logger.error(f"Failed to update personality for channel {channel_id}")
				return False
		except Exception as e:
			self.logger.error(f"Failed to update channel personality: {e}")
			raise
