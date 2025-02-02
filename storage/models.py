from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Wallet:
    address: str
    chain: str
    added_at: datetime

@dataclass
class Personality:
    name: str
    traits: List[str]
    interests: List[str]
    communication_style: str
    created_at: datetime
    updated_at: datetime
    post_count: int
    raw_analysis: dict

@dataclass
class Channel:
    username: str
    title: Optional[str]
    added_at: datetime
    wallets: List[Wallet]
    personality: Optional[Personality]
    user_id: int