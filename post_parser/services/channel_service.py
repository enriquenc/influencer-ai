import logging
from telethon.sync import TelegramClient
from telethon.tl.types import Channel

class ChannelService:
    def __init__(self, client: TelegramClient):
        self.client = client

    async def cleanup_username(self, username: str) -> str:
        if username.startswith('@'):
            return username
        else:
            return '@' + username.split('/')[-1]

    async def check_admin_rights(self, channel_entity, admin_id: int) -> bool:
        ADMIN_RIGHTS_REQUEST = """
        Please add the bot as an administrator to the channel with these permissions:
                                    ✓ Send Messages
                                    ✓ Edit Messages
                                    ✓ Delete Messages
                                    ✓ Post Messages"""
        try:
            permission = await self.client.get_permissions(channel_entity, admin_id)
            return permission.is_admin
        except Exception as e:
            logging.error(f"Error checking admin rights: {e}")
            return False

    async def get_channel_entity(self, channel_username: str) -> Channel:
        try:
            channel = await self.client.get_entity(channel_username)
            if not isinstance(channel, Channel):
                raise ValueError("Not a valid channel")
            return channel
        except Exception as e:
            logging.error(f"Error getting channel entity: {e}")
            raise