import logging
from telethon.sync import TelegramClient
from telethon.tl.types import Channel
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.functions.channels import JoinChannelRequest
from aiogram import Bot
from aiogram.types import ChatMemberAdministrator

class ChannelService:
    def __init__(self, client: TelegramClient, bot_token: str):
        self.client = client
        self.bot = Bot(token=bot_token)  # Create bot instance for permission checks
        self.logger = logging.getLogger(__name__)

    async def cleanup_username(self, username: str) -> str:
        if username.startswith('@'):
            return username
        else:
            return '@' + username.split('/')[-1]

    async def check_admin_rights(self, channel_entity, admin_id: int) -> bool:
        """Check admin rights with detailed logging"""
        try:
            channel_id = f"-100{channel_entity.id}"
            self.logger.info(f"Checking bot rights for channel {channel_entity.title} (ID: {channel_id})")

            bot_member = await self.bot.get_chat_member(
                chat_id=channel_id,
                user_id=self.bot.id
            )

            self.logger.info(f"Bot ID: {self.bot.id}")
            self.logger.info(f"Member type: {type(bot_member)}")

            if not isinstance(bot_member, ChatMemberAdministrator):
                self.logger.warning("Bot is not an admin")
                return False

            # Check specific rights
            required_rights = {
                'Post Messages': bot_member.can_post_messages,
                'Edit Messages': bot_member.can_edit_messages,
                'Delete Messages': bot_member.can_delete_messages,
                'Send Messages': True  # Always True for channels
            }

            self.logger.info(f"Required rights check: {required_rights}")

            if not all(required_rights.values()):
                missing = [right for right, has_right in required_rights.items() if not has_right]
                self.logger.warning(f"Missing rights: {missing}")
                raise ChatAdminRequiredError(
                    "Bot needs the following permissions enabled:\n\n"
                    "To fix this:\n"
                    "1. Go to channel settings\n"
                    "2. Click on Administrators\n"
                    "3. Find the bot and edit its permissions\n"
                    "4. Enable these permissions:\n"
                    "   " + "\n   ".join(f"• {right}" for right in missing)
                )

            return True

        except ChatAdminRequiredError:
            raise
        except Exception as e:
            self.logger.error(f"Error checking admin rights: {e}", exc_info=True)
            return False

    async def get_channel_entity(self, channel_username: str) -> Channel:
        try:
            channel = await self.client.get_entity(channel_username)
            if not isinstance(channel, Channel):
                raise ValueError("Not a valid channel")
            return channel
        except Exception as e:
            self.logger.error(f"Error getting channel entity: {e}")
            raise

    async def ensure_bot_joined(self, channel) -> bool:
        """Ensure bot has joined the channel"""
        try:
            await self.client(JoinChannelRequest(channel))
            self.logger.info(f"Successfully joined channel: {channel.title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to join channel: {e}")
            return False

    async def get_permissions_info(self, channel_username: str) -> str:
        """Get formatted string of bot's permissions for a channel"""
        try:
            channel = await self.get_channel_entity(f"@{channel_username}")
            channel_id = f"-100{channel.id}"

            bot_member = await self.bot.get_chat_member(
                chat_id=channel_id,
                user_id=self.bot.id
            )

            # Check key permissions
            rights = {
                'Admin': isinstance(bot_member, ChatMemberAdministrator),
                'Post Messages': getattr(bot_member, 'can_post_messages', False) if isinstance(bot_member, ChatMemberAdministrator) else False,
                'Edit Messages': getattr(bot_member, 'can_edit_messages', False) if isinstance(bot_member, ChatMemberAdministrator) else False,
                'Delete Messages': getattr(bot_member, 'can_delete_messages', False) if isinstance(bot_member, ChatMemberAdministrator) else False,
                'Send Messages': isinstance(bot_member, ChatMemberAdministrator)  # True if admin
            }

            # Format permissions string
            rights_text = []
            for right, has_right in rights.items():
                icon = "✅" if has_right else "❌"
                rights_text.append(f"{icon} {right}")

            return "\n".join(rights_text)

        except Exception as e:
            self.logger.error(f"Error getting permissions for @{channel_username}: {e}")
            return (
                "❌ Could not access channel\n"
                "Please ensure:\n"
                "1. Bot is added to the channel\n"
                "2. Bot is an admin\n"
                "3. Channel is accessible"
            )

    async def send_message(self, channel_username: str, message: str) -> bool:
        """Send message to channel with admin rights check"""
        try:
            channel_username = channel_username.lstrip('@')
            channel = await self.get_channel_entity(f"@{channel_username}")
            channel_id = f"-100{channel.id}"

            # Check bot's permissions
            bot_member = await self.bot.get_chat_member(
                chat_id=channel_id,
                user_id=self.bot.id
            )

            if not isinstance(bot_member, ChatMemberAdministrator):
                raise ChatAdminRequiredError("Bot is not an admin in this channel")

            # Check specific permissions
            if not bot_member.can_post_messages:
                raise ChatAdminRequiredError(
                    "Bot needs 'Post Messages' permission.\n"
                    "Please enable it in channel admin settings."
                )

            # Send message using aiogram's bot instance
            await self.bot.send_message(
                chat_id=channel_id,
                text=message
            )
            return True

        except ChatAdminRequiredError:
            raise
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise

    async def _get_missing_permissions(self, channel, bot_id) -> str:
        """Helper to get list of missing permissions"""
        try:
            permissions = await self.client.get_permissions(channel, bot_id)
            missing = []

            if not getattr(permissions, 'post_messages', False):
                missing.append("✗ Post Messages")
            if not getattr(permissions, 'edit_messages', False):
                missing.append("✗ Edit Messages")
            if not getattr(permissions, 'delete_messages', False):
                missing.append("✗ Delete Messages")
            if not getattr(permissions, 'send_messages', False):
                missing.append("✗ Send Messages")

            return "\n".join(missing) if missing else "All required permissions are granted"

        except Exception as e:
            self.logger.error(f"Error checking missing permissions: {e}")
            return "Could not check permissions"