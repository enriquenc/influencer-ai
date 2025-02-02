from typing import Dict, List, Optional
from datetime import datetime
from post_parser.config import load_config
from personality_analyzer import load_config
from .models import Channel, Wallet, Personality
from .mongo import MongoDBSingleton
from .local_storage import LocalStorage
from .base_storage import BaseStorage

"""
Canonical storage implementation for the post parser application.
Handles in-memory storage of channels, wallets, and personalities.

This is the single source of truth for data storage in the application.
"""
config = load_config()

class Storage(BaseStorage):
    """Storage factory that returns either MongoDB or local storage based on config"""
    
    def __init__(self):
        mongo_uri = config.get("mongo", {}).get("uri")
        if mongo_uri:
            self._storage = MongoDBSingleton(
                mongo_uri,
                config["mongo"]["db_name"]
            )
        else:
            self._storage = LocalStorage()

    async def get_channel(self, username: str) -> Optional[Channel]:
        """Get channel by username"""
        return await self._storage.get_channel(username)

    async def get_user_channels(self, user_id: int) -> List[Channel]:
        """Get all channels for a user"""
        return await self._storage.get_user_channels(user_id)

    async def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        """Add a new channel"""
        return await self._storage.add_channel(user_id, username, title)

    async def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        """Add wallet to channel"""
        return await self._storage.add_wallet(username, wallet_address, chain)

    async def update_channel_personality(self, username: str, personality: Personality) -> bool:
        """Update channel personality"""
        return await self._storage.update_channel_personality(username, personality)

    async def get_channel_wallets(self, username: str) -> List[Wallet]:
        """Get all wallets for a channel"""
        return await self._storage.get_channel_wallets(username)
