from typing import Dict, List, Optional
from datetime import datetime
from .models import Channel, Wallet, Personality

class Storage:
    """In-memory storage for channels, wallets, and personalities"""
    def __init__(self):
        self.channels: Dict[str, Channel] = {}
        self.user_channels: Dict[int, List[str]] = {}

    def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        if username.startswith('@'):
            username = username[1:]

        channel = Channel(
            username=username,
            title=title,
            added_at=datetime.utcnow(),
            wallets=[],
            personality=None
        )

        self.channels[username] = channel

        if user_id not in self.user_channels:
            self.user_channels[user_id] = []

        if username not in self.user_channels[user_id]:
            self.user_channels[user_id].append(username)

        return channel

    def update_channel_personality(self, username: str, personality: Personality) -> Optional[Channel]:
        """Update channel's personality analysis"""
        if username.startswith('@'):
            username = username[1:]

        channel = self.channels.get(username)
        if channel:
            channel.personality = personality
            return channel
        return None

    def add_wallet(self, username: str, wallet_address: str, chain: str = "ethereum") -> Optional[Wallet]:
        if username.startswith('@'):
            username = username[1:]

        channel = self.channels.get(username)
        if not channel:
            return None

        wallet = Wallet(
            address=wallet_address,
            chain=chain,
            added_at=datetime.now()
        )

        channel.wallets.append(wallet)
        return wallet

    def get_user_channels(self, user_id: int) -> List[Channel]:
        usernames = self.user_channels.get(user_id, [])
        return [self.channels[username] for username in usernames if username in self.channels]

    def get_channel_wallets(self, username: str) -> List[Wallet]:
        if username.startswith('@'):
            username = username[1:]

        channel = self.channels.get(username)
        return channel.wallets if channel else []