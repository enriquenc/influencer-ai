from typing import Dict, List, Optional
from datetime import datetime
from post_parser.config import load_config
from personality_analyzer import load_config
from .models import Channel, Wallet, Personality
from .mongo import MongoDBSingleton

"""
Canonical storage implementation for the post parser application.
Handles in-memory storage of channels, wallets, and personalities.

This is the single source of truth for data storage in the application.
"""
config = load_config()

class Storage:

    mongo_singleton = MongoDBSingleton(
        config["mongo"]["uri"],
        config["mongo"]["db_name"]
    )

    """In-memory storage for channels, wallets, and personalities"""
    def __init__(self):
        self.channels: Dict[str, Channel] = {}  # username -> Channel
        self.user_channels: Dict[int, List[str]] = {}  # user_id -> [channel_usernames]

    def get_channel(self, username: str) -> Optional[Channel]:
       return mongo_singleton.get_channel(username)

    def get_user_channels(self, user_id: int) -> List[Channel]:
        return mongo_singleton.get_user_channels(user_id)

    def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        return mongo_singleton.add_channel(user_id, username, title)

    def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        return mongo_singleton.add_wallet(username, wallet_address, chain)

    def update_channel_personality(self, username: str, personality: Personality) -> bool:
        return mongo_singleton.update_channel_personality(username, personality)

    def get_channel_wallets(self, username: str) -> List[Wallet]:
        return mongo_singleton.get_channel_wallets(username)
