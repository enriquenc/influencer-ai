from typing import Dict, List, Optional
from datetime import datetime
from .models import Channel, Wallet, Personality
import logging

"""
Canonical storage implementation for the post parser application.
Handles in-memory storage of channels, wallets, and personalities.

This is the single source of truth for data storage in the application.
"""

logger = logging.getLogger(__name__)

class Storage:
    """In-memory storage for channels, wallets, and personalities"""
    def __init__(self):
        self.channels: Dict[str, Channel] = {}  # username -> Channel
        self.user_channels: Dict[int, List[str]] = {}  # user_id -> [channel_usernames]
        self._migrate_channels()

    def _migrate_channels(self):
        """Migrate existing channels to include user_id"""
        for username, channel in self.channels.items():
            if not hasattr(channel, 'user_id'):
                # Find user_id from user_channels
                for user_id, usernames in self.user_channels.items():
                    if username in usernames:
                        channel.user_id = user_id
                        break

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
            # Update user_id if not set
            if not hasattr(channel, 'user_id'):
                channel.user_id = user_id
        else:
            channel = Channel(
                username=username,
                title=title,
                added_at=datetime.utcnow(),
                wallets=[],
                personality=None,
                user_id=user_id  # Store user_id in channel
            )
            self.channels[username] = channel

        # Link to user if not already linked
        if user_id not in self.user_channels:
            self.user_channels[user_id] = []
        if username not in self.user_channels[user_id]:
            self.user_channels[user_id].append(username)

        return channel

    def add_wallet(self, channel_username: str, wallet_address: str, chain: str = "Base") -> Optional[Wallet]:
        """Add wallet to channel and subscribe to updates"""
        try:
            # Get user_id for the channel
            channel = self.get_channel(channel_username)
            if not channel:
                return None

            # Create wallet record
            wallet = Wallet(
                address=wallet_address,
                chain=chain,
                added_at=datetime.utcnow()
            )

            # Add to channel's wallets
            if not channel.wallets:
                channel.wallets = []
            channel.wallets.append(wallet)

            return wallet

        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return None

    def get_user_id_for_wallet(self, wallet_address: str) -> Optional[int]:
        """Get user_id associated with a wallet address"""
        try:
            logger.info(f"Looking up user_id for wallet {wallet_address}")
            for channel in self.channels.values():
                logger.debug(f"Checking channel {channel.username}")
                if channel.wallets:
                    for wallet in channel.wallets:
                        logger.debug(f"Checking wallet {wallet.address}")
                        if wallet.address.lower() == wallet_address.lower():
                            logger.info(f"Found user_id {channel.user_id} for wallet {wallet_address}")
                            return channel.user_id
            logger.warning(f"No channel found with wallet {wallet_address}")
            return None
        except Exception as e:
            logger.error(f"Error getting user_id for wallet: {e}", exc_info=True)
            return None

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