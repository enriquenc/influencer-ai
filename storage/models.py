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
    personality: Optional[Personality] = None  # New field for personality