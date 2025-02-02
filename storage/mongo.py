import logging
import motor.motor_asyncio
from datetime import datetime
from typing import List, Optional, Dict
from bson import ObjectId
import json
from .base_storage import BaseStorage
from .models import Channel, Wallet, Personality

class Singleton:
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cls] = instance
            instance.__initialized = False
        return cls._instances[cls]

class MongoDBSingleton(BaseStorage):
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

    async def get_channel(self, username: str) -> Optional[Channel]:
        """Get channel by username from MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')
        try:
            channel_data = await collection.find_one({"username": username})
            return Channel.from_dict(channel_data) if channel_data else None
        except Exception as e:
            self.logger.error(f"Failed to get channel: {e}")
            return None

    async def get_user_channels(self, user_id: int) -> List[Channel]:
        """Get all channels for a user from MongoDB"""
        collection = await self.get_collection('channel')
        try:
            channels_data = await collection.find({"user_id": user_id}).to_list(None)
            return [Channel.from_dict(channel) for channel in channels_data]
        except Exception as e:
            self.logger.error(f"Failed to get user channels: {e}")
            return []

    async def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        """Add channel to MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        try:
            # Check if channel already exists
            channel_data = await collection.find_one({"username": username})
            if not channel_data:
                # Create a new channel
                channel_data = {
                    "username": username,
                    "title": title,
                    "added_at": datetime.utcnow(),
                    "wallets": [],
                    "personality": None,
                    "user_id": user_id
                }
                await collection.insert_one(channel_data)
            else:
                # Update user_id if it doesn't match
                if "user_id" not in channel_data or channel_data["user_id"] != user_id:
                    await collection.update_one(
                        {"username": username},
                        {"$set": {"user_id": user_id}}
                    )
                    channel_data["user_id"] = user_id

            return Channel.from_dict(channel_data)
        except Exception as e:
            self.logger.error(f"Failed to add channel: {e}")
            raise

    async def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        """Add wallet to channel in MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        wallet_data = {
            "address": wallet_address,
            "chain": chain,
            "added_at": datetime.utcnow()
        }

        try:
            result = await collection.update_one(
                {"username": username},
                {"$push": {"wallets": wallet_data}}
            )
            if result.modified_count > 0:
                return Wallet.from_dict(wallet_data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to add wallet: {e}")
            return None

    async def update_channel_personality(self, username: str, personality: Personality) -> bool:
        """Update channel's personality analysis in MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        try:
            # Convert Personality object to dictionary
            if hasattr(personality, 'to_json'):
                personality_dict = json.loads(personality.to_json())
            else:
                personality_dict = personality.__dict__

            result = await collection.update_one(
                {"username": username},
                {"$set": {"personality": personality_dict}}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Failed to update channel personality: {e}")
            return False

    async def get_channel_wallets(self, username: str) -> List[Wallet]:
        """Get all wallets for a channel from MongoDB"""
        username = username.lstrip('@')
        collection = await self.get_collection('channel')

        try:
            channel = await collection.find_one({"username": username})
            if not channel:
                return []
            return [Wallet.from_dict(w) for w in channel.get("wallets", [])]
        except Exception as e:
            self.logger.error(f"Failed to get channel wallets: {e}")
            return []
