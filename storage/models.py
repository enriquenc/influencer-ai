from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from personality_analyzer import Personality

@dataclass
class Wallet:
    address: str
    chain: str
    added_at: datetime

@dataclass
class Channel:
    username: str
    title: Optional[str]
    added_at: datetime
    wallets: List[Wallet]
    personality: Optional[Personality] = None

class Storage:
    def __init__(self):
        self.channels = {}
        self.user_channels = {}

    def get_channel(self, username: str):
        """Get channel by username"""
        # Remove @ if present
        username = username.lstrip('@')

        # Search through all channels
        for channels in self.user_channels.values():
            for channel in channels:
                if channel.username == username:
                    return channel
        return None

    def get_user_channels(self, user_id: int):
        """Get all channels for a user"""
        return self.user_channels.get(user_id, [])

    def add_channel(self, user_id: int, username: str, title: str):
        """Add a channel for a user"""
        # Initialize user's channels list if not exists
        if user_id not in self.user_channels:
            self.user_channels[user_id] = []

        # Remove @ if present
        username = username.lstrip('@')

        # Check if channel already exists for this user
        for channel in self.user_channels[user_id]:
            if channel.username == username:
                return channel

        # Create new channel
        new_channel = Channel(
            username=username,
            title=title,
            added_at=datetime.utcnow(),
            wallets=[],
            personality=None
        )

        # Add to user's channels
        self.user_channels[user_id].append(new_channel)
        return new_channel

    def add_wallet(self, channel_username: str, wallet_address: str, chain: str = "Base"):
        """Add wallet to channel"""
        channel = self.get_channel(channel_username)
        if not channel:
            return None

        # Create new wallet
        new_wallet = Wallet(
            address=wallet_address,
            chain=chain,
            added_at=datetime.utcnow()
        )

        # Add to channel's wallets
        channel.wallets.append(new_wallet)
        return new_wallet

    def update_channel_personality(self, channel_username: str, personality: Personality):
        """Update channel's personality"""
        channel = self.get_channel(channel_username)
        if channel:
            channel.personality = personality
            return True
        return False