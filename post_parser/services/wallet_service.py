import logging
from typing import Optional, Tuple
from aiogram import Bot
from onchain_parser.api import subscribe_to_wallet, unsubscribe_from_wallet
from onchain_parser.models import TransactionEvent
from onchain_parser.monitor_service import monitor_service
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class WalletService:
    def __init__(self, bot: Bot, storage, personality_analyzer, fsm_storage):
        self.bot = bot
        self.storage = storage
        self.personality_analyzer = personality_analyzer
        self.fsm_storage = fsm_storage
        self._loop = asyncio.get_event_loop()
        logger.info("WalletService initialized")

    def get_channel_for_wallet(self, wallet_address: str) -> Tuple[Optional[str], Optional[int]]:
        """Get channel username and user_id for a wallet"""
        for channel in self.storage.channels.values():
            if channel.wallets:
                for wallet in channel.wallets:
                    if wallet.address.lower() == wallet_address.lower():
                        return channel.username, channel.user_id
        return None, None

    def _create_post_keyboard(self, channel_username: str, is_transaction: bool = True) -> InlineKeyboardMarkup:
        """Create keyboard for post actions"""
        builder = InlineKeyboardBuilder()

        # Add post to channel button
        builder.button(
            text="📢 Post to channel",
            callback_data=f"post_to_channel:{channel_username}"
        )

        # Add regenerate button with transaction context if it's a transaction post
        if is_transaction:
            builder.button(
                text="🔄 Regenerate",
                callback_data=f"regenerate_tx_post:{channel_username}"
            )
        else:
            builder.button(
                text="🔄 Regenerate",
                callback_data=f"regenerate_post:{channel_username}"
            )

        builder.adjust(1)  # One button per row
        return builder.as_markup()

    async def generate_post_proposal(self, tx_event: TransactionEvent, channel_username: str) -> str:
        """Generate post proposal based on transaction and channel personality"""
        try:
            channel = self.storage.get_channel(channel_username)
            if not channel or not channel.personality:
                return self.format_default_post(tx_event)

            # Format transaction details
            tx_type = 'SELL' if tx_event.transfers and tx_event.transfers[0].operation == 'SELL' else 'BUY'
            token = tx_event.transfers[0].token.symbol if tx_event.transfers else 'ETH'
            amount = tx_event.transfers[0].amount if tx_event.transfers else tx_event.value
            price = tx_event.transfers[0].token.price if tx_event.transfers else 'N/A'

            # Use personality to generate custom post
            prompt = f"""Generate a Telegram post with the following characteristics:

Personality Traits: {', '.join(channel.personality.traits[:3])}
Main Interests: {', '.join(channel.personality.interests[:3])}
Communication Style: {channel.personality.communication_style}

Transaction Details:
- Operation: {tx_type}
- Token: {token}
- Amount: {amount}
- Price: ${price}

Requirements:
1. Match the communication style exactly
2. Focus on explaining WHY this {tx_type} transaction was made
3. Express the personality traits naturally
4. Be concise and engaging
5. Include relevant emojis
6. Format appropriately for Telegram
7. Explain the reasoning behind the {tx_type} decision based on the personality traits and interests
8. Include brief market analysis or strategic thinking if it matches the personality

Generate a single post that explains the transaction and reasoning:"""

            try:
                response = self.personality_analyzer.generate_post(prompt)
                if response:
                    return response
            except Exception as e:
                logger.error(f"Error generating post: {e}", exc_info=True)

            return self.format_default_post(tx_event)

        except Exception as e:
            logger.error(f"Error in generate_post_proposal: {e}", exc_info=True)
            return self.format_default_post(tx_event)

    def format_default_post(self, tx_event: TransactionEvent) -> str:
        """Format default post when personality-based generation fails"""
        try:
            if tx_event.transfers:
                transfer = tx_event.transfers[0]
                total_value_str = f"${transfer.total_value:.2f}" if transfer.total_value else "N/A"
                return (
                    f"🔔 New {transfer.operation} Transaction!\n\n"
                    f"Token: {transfer.token.symbol}\n"
                    f"Amount: {transfer.amount}\n"
                    f"Price: ${transfer.token.price:.4f}\n"
                    f"Total Value: {total_value_str}"
                )
            else:
                return (
                    f"🔔 New ETH Transaction!\n\n"
                    f"Amount: {tx_event.value} ETH\n"
                    f"From: {tx_event.from_address[:8]}...\n"
                    f"To: {tx_event.to_address[:8]}..."
                )
        except Exception as e:
            logger.error(f"Error formatting default post: {e}", exc_info=True)
            return "Failed to format transaction post"

    async def handle_transaction(self, tx_event: TransactionEvent, wallet_address: str):
        """Handle incoming transaction event"""
        try:
            # Get channel info for the wallet
            channel_username, user_id = self.get_channel_for_wallet(wallet_address)
            if not user_id:
                logger.warning(f"No user found for wallet {wallet_address}")
                return

            logger.info(f"Processing transaction for wallet {wallet_address}")

            # Store transaction event in state
            state = FSMContext(
                storage=self.fsm_storage,
                key=f'user_{user_id}'
            )
            await state.set_data({'current_tx_event': tx_event})

            # Send transaction notification
            tx_message = (
                f"🔔 New transaction detected!\n\n"
                f"{tx_event.format_brief()}"
            )
            await self.bot.send_message(
                chat_id=user_id,
                text=tx_message
            )
            logger.info(f"Transaction notification sent to user {user_id}")

            # Generate and send post proposal
            if channel_username:
                try:
                    post_proposal = await self.generate_post_proposal(tx_event, channel_username)
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"📝 Suggested post for @{channel_username}:\n\n"
                            f"{post_proposal}"
                        ),
                        reply_markup=self._create_post_keyboard(channel_username)
                    )
                    logger.info(f"Post proposal sent to user {user_id}")
                except Exception as e:
                    logger.error(f"Error generating/sending post proposal: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling transaction: {e}", exc_info=True)

    def _sync_callback(self, tx_event: TransactionEvent, wallet_address: str):
        """Synchronous wrapper for async callback"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.handle_transaction(tx_event, wallet_address),
                self._loop
            )
            future.result()  # Wait for completion
        except Exception as e:
            logger.error(f"Error in sync callback: {e}", exc_info=True)

    def subscribe_wallet(self, wallet_address: str) -> bool:
        """Subscribe to wallet updates"""
        try:
            logger.info(f"Subscribing to wallet {wallet_address}")
            success = subscribe_to_wallet(
                wallet_address=wallet_address,
                callback=lambda tx: self._sync_callback(tx, wallet_address)
            )
            if success:
                logger.info(f"Successfully subscribed to wallet {wallet_address}")
            else:
                logger.warning(f"Failed to subscribe to wallet {wallet_address}")
            return success
        except Exception as e:
            logger.error(f"Error subscribing to wallet: {e}")
            return False