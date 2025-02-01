from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Wallet:
    address: str
    chain: str  # e.g., "ethereum", "solana", etc.
    added_at: datetime

@dataclass
class Channel:
    username: str
    title: Optional[str]
    added_at: datetime
    wallets: List[Wallet]

class Storage:
    """In-memory storage for channels and wallets"""
    def __init__(self):
        self.channels: Dict[str, Channel] = {}  # username -> Channel
        self.user_channels: Dict[int, List[str]] = {}  # user_id -> [channel_usernames]

    def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        """Add channel to storage and link it to user"""
        if username.startswith('@'):
            username = username[1:]

        channel = Channel(
            username=username,
            title=title,
            added_at=datetime.utcnow(),
            wallets=[]
        )

        self.channels[username] = channel

        if user_id not in self.user_channels:
            self.user_channels[user_id] = []

        if username not in self.user_channels[user_id]:
            self.user_channels[user_id].append(username)

        return channel

    def add_wallet(self, username: str, wallet_address: str, chain: str = "ethereum") -> Optional[Wallet]:
        """Add wallet to channel"""
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
        """Get all channels for user"""
        usernames = self.user_channels.get(user_id, [])
        return [self.channels[username] for username in usernames if username in self.channels]

    def get_channel_wallets(self, username: str) -> List[Wallet]:
        """Get all wallets for channel"""
        if username.startswith('@'):
            username = username[1:]

        channel = self.channels.get(username)
        return channel.wallets if channel else []