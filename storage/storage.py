from typing import Dict, List, Optional
from datetime import datetime
from .models import Channel, Wallet, Personality

"""
Canonical storage implementation for the post parser application.
Handles in-memory storage of channels, wallets, and personalities.

This is the single source of truth for data storage in the application.
"""

class Storage:
    """In-memory storage for channels, wallets, and personalities"""
    def __init__(self):
        self.channels: Dict[str, Channel] = {}  # username -> Channel
        self.user_channels: Dict[int, List[str]] = {}  # user_id -> [channel_usernames]

    def get_channel(self, username: str) -> Optional[Channel]:
        """Get channel by username"""
        username = username.lstrip('@')
        return self.channels.get(username)

    def get_user_channels(self, user_id: int) -> List[Channel]:
        """Get all channels for a user"""
        usernames = self.user_channels.get(user_id, [])
        return [self.channels[username] for username in usernames if username in self.channels]

    def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        """Add channel to storage and link it to user"""
        username = username.lstrip('@')

        # Check if channel already exists
        if username in self.channels:
            channel = self.channels[username]
        else:
            channel = Channel(
                username=username,
                title=title,
                added_at=datetime.utcnow(),
                wallets=[],
                personality=None
            )
            self.channels[username] = channel

        # Link to user if not already linked
        if user_id not in self.user_channels:
            self.user_channels[user_id] = []
        if username not in self.user_channels[user_id]:
            self.user_channels[user_id].append(username)

        return channel

    def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        """Add wallet to channel"""
        username = username.lstrip('@')
        channel = self.channels.get(username)
        if not channel:
            return None

        wallet = Wallet(
            address=wallet_address,
            chain=chain,
            added_at=datetime.utcnow()
        )
        channel.wallets.append(wallet)
        return wallet

    def update_channel_personality(self, username: str, personality: Personality) -> bool:
        """Update channel's personality analysis"""
        username = username.lstrip('@')
        channel = self.channels.get(username)
        if channel:
            channel.personality = personality
            return True
        return False

    def get_channel_wallets(self, username: str) -> List[Wallet]:
        """Get all wallets for a channel"""
        username = username.lstrip('@')
        channel = self.channels.get(username)
        return channel.wallets if channel else []