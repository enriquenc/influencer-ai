from datetime import datetime
from typing import Dict, List, Optional
from .base_storage import BaseStorage
from .models import Channel, Wallet, Personality

class LocalStorage(BaseStorage):
    def __init__(self):
        self.channels: Dict[str, Channel] = {}
        self.user_channels: Dict[int, List[str]] = {}

    async def get_channel(self, username: str) -> Optional[Channel]:
        return self.channels.get(username.lstrip('@'))

    async def get_user_channels(self, user_id: int) -> List[Channel]:
        usernames = self.user_channels.get(user_id, [])
        return [self.channels[username] for username in usernames if username in self.channels]

    async def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        username = username.lstrip('@')
        if username not in self.channels:
            channel = Channel(
                username=username,
                title=title,
                added_at=datetime.utcnow(),
                wallets=[],
                personality=None,
                user_id=user_id
            )
            self.channels[username] = channel
            if user_id not in self.user_channels:
                self.user_channels[user_id] = []
            self.user_channels[user_id].append(username)
        return self.channels[username]

    async def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        username = username.lstrip('@')
        if username not in self.channels:
            return None
        
        wallet = Wallet(
            address=wallet_address,
            chain=chain,
            added_at=datetime.utcnow()
        )
        self.channels[username].wallets.append(wallet)
        return wallet

    async def update_channel_personality(self, username: str, personality: Personality) -> bool:
        username = username.lstrip('@')
        if username not in self.channels:
            return False
        self.channels[username].personality = personality
        return True

    async def get_channel_wallets(self, username: str) -> List[Wallet]:
        username = username.lstrip('@')
        if username not in self.channels:
            return []
        return self.channels[username].wallets 