from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from personality_analyzer import Personality

@dataclass
class Wallet:
    address: str
    chain: str
    added_at: datetime

    @classmethod
    def from_dict(cls, data: Dict) -> 'Wallet':
        return cls(
            address=data['address'],
            chain=data['chain'],
            added_at=datetime.fromisoformat(data['added_at']) if isinstance(data['added_at'], str) else data['added_at']
        )

@dataclass
class Channel:
    username: str
    title: Optional[str]
    added_at: datetime
    wallets: List[Wallet]
    personality: Optional[Personality]
    user_id: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'Channel':
        personality_data = data.get('personality')
        personality = Personality(**personality_data) if personality_data else None

        return cls(
            username=data['username'],
            title=data.get('title'),
            added_at=datetime.fromisoformat(data['added_at']) if isinstance(data['added_at'], str) else data['added_at'],
            wallets=[Wallet.from_dict(w) for w in data.get('wallets', [])],
            personality=personality,
            user_id=data['user_id']
        )