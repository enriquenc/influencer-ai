from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Channel, Wallet, Personality

class BaseStorage(ABC):
    """Abstract base class for storage implementations"""
    
    @abstractmethod
    async def get_channel(self, username: str) -> Optional[Channel]:
        pass
    
    @abstractmethod
    async def get_user_channels(self, user_id: int) -> List[Channel]:
        pass
    
    @abstractmethod
    async def add_channel(self, user_id: int, username: str, title: Optional[str] = None) -> Channel:
        pass
    
    @abstractmethod
    async def add_wallet(self, username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        pass
    
    @abstractmethod
    async def update_channel_personality(self, username: str, personality: Personality) -> bool:
        pass
    
    @abstractmethod
    async def get_channel_wallets(self, username: str) -> List[Wallet]:
        pass 