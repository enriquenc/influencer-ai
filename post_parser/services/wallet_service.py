import logging
from typing import Optional
from aiogram import Bot
from onchain_parser.api import subscribe_to_wallet, unsubscribe_from_wallet
from onchain_parser.models import TransactionEvent
from onchain_parser.monitor_service import monitor_service  # Import the singleton
import asyncio

logger = logging.getLogger(__name__)

class WalletService:
    def __init__(self, bot: Bot, storage):
        self.bot = bot
        self.storage = storage
        self._loop = asyncio.get_event_loop()
        logger.info("WalletService initialized")

    async def handle_transaction(self, tx_event: TransactionEvent, wallet_address: str):
        """Handle incoming transaction event"""
        try:
            # Get user_id for the wallet
            user_id = self.storage.get_user_id_for_wallet(wallet_address)
            if not user_id:
                logger.warning(f"No user found for wallet {wallet_address}")
                return

            logger.info(f"Processing transaction for wallet {wallet_address}")

            # Format message
            message = (
                f"🔔 New transaction detected!\n\n"
                f"{tx_event.format_brief()}"
            )

            # Send notification to user
            await self.bot.send_message(
                chat_id=user_id,
                text=message
            )
            logger.info(f"Transaction notification sent to user {user_id}")

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