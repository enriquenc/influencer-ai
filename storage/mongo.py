import logging
import motor.motor_asyncio
from datetime import datetime
from typing import List, Optional, Dict
from bson import ObjectId

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

    async def get_channel(self, username: str) -> Optional[Dict]:
        """Get channel by username from MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')
        try:
            channel = await collection.find_one({"username": username})
            return channel
        except Exception as e:
            self.logger.error(f"Failed to get channel: {e}")
            return None

    async def get_user_channels(self, user_id: int) -> List[Dict]:
        """Get all channels for a user from MongoDB"""
        collection = await self.get_collection('channel')
        try:
            channels = await collection.find({"user_id": user_id}).to_list(None)
            return channels
        except Exception as e:
            self.logger.error(f"Failed to get user channels: {e}")
            return []

    async def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Dict:
        """Add channel to MongoDB and link it to user"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        # Check if channel already exists
        channel = await collection.find_one({"username": username})
        if not channel:
            # Create a new channel
            channel = {
                "username": username,
                "title": title,
                "added_at": datetime.utcnow(),
                "wallets": [],
                "personality": None,
                "user_id": user_id
            }
            await collection.insert_one(channel)
        else:
            # Update user_id if it doesn't match
            if "user_id" not in channel or channel["user_id"] != user_id:
                await collection.update_one(
                    {"username": username},
                    {"$set": {"user_id": user_id}}
                )

        return channel

    async def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Dict]:
        """Add wallet to channel in MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        wallet = {
            "address": wallet_address,
            "chain": chain,
            "added_at": datetime.utcnow()
        }

        try:
            result = await collection.update_one(
                {"username": username},
                {"$push": {"wallets": wallet}}
            )
            if result.modified_count > 0:
                return wallet
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to add wallet: {e}")
            return None

    async def update_channel_personality(self, username: str, personality: Dict) -> bool:
        """Update channel's personality analysis in MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        try:
            result = await collection.update_one(
                {"username": username},
                {"$set": {"personality": personality}}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Failed to update channel personality: {e}")
            return False

    async def get_channel_wallets(self, username: str) -> List[Dict]:
        """Get all wallets for a channel from MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        try:
            channel = await collection.find_one({"username": username})
            return channel.get("wallets", []) if channel else []
        except Exception as e:
            self.logger.error(f"Failed to get channel wallets: {e}")
            return []
