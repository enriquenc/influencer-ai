import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from telethon.tl.types import Channel
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..bot.states import AddChannel, AddWallet, WalletList
from ..bot.responses import AIPersonality
from ..bot.callbacks import ChannelAction

logger = logging.getLogger(__name__)

def setup_handlers(
    router: Router,
    channel_storage,
    channel_service,
    parser_service,
    personality_analyzer,
    log_service
) -> None:
    """Setup all bot command handlers"""

    async def parse_channel_messages(message: types.Message, channel_username: str):
        """Parse and analyze channel messages"""
        try:
            parsed_messages = await parser_service.parse_channel(channel_username)

            # Analyze personality
            personality = personality_analyzer.analyze_posts(parsed_messages)

            # Update storage with personality
            channel_storage.update_channel_personality(channel_username, personality)

            # Save personality to logs
            log_service.save_personality(channel_username, personality)

            # Log analysis results
            logger.info(
                f"Personality analysis for {channel_username}:\n"
                f"Traits: {', '.join(personality.traits)}\n"
                f"Interests: {', '.join(personality.interests)}\n"
                f"Communication Style: {personality.communication_style}"
            )

            await message.answer(
                f"""✨ Analysis complete! I've processed {len(parsed_messages)} posts from {channel_username}.

Personality Profile:
- Traits: {', '.join(personality.traits[:3])}
- Main Interests: {', '.join(personality.interests[:3])}

The complete data has been saved!
                """
            )
        except Exception as e:
            logger.error(f"Error analyzing messages: {str(e)}", exc_info=True)
            await message.answer("Sorry! I encountered an issue while analyzing the channel. Please try again later.")

    @router.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(AIPersonality.WELCOME_MESSAGE)

    @router.message(Command("add_channel"))
    async def add_channel_start(message: types.Message, state: FSMContext):
        await message.reply("Please provide a channel username starting with @ or link to it")
        await state.set_state(AddChannel.waiting_for_channel)

    @router.message(AddChannel.waiting_for_channel)
    async def add_channel_finish(message: types.Message, state: FSMContext):
        try:
            channel_username = message.text
            logger.info(f"Received channel username: {channel_username}")

            # Format check and conversion
            if channel_username.startswith('https://t.me/'):
                channel_username = await channel_service.cleanup_username(channel_username)
            elif not channel_username.startswith('@'):
                await message.reply("❌ Please provide a valid channel username starting with @ or a t.me link")
                return

            try:
                # Send initial processing message
                processing_msg = await message.reply(
                    "⏳ Processing your request...\n"
                    "1. Verifying channel access..."
                )

                channel = await channel_service.get_channel_entity(channel_username)
                logger.info(f"Channel info retrieved: {channel}")

                await processing_msg.edit_text(
                    "⏳ Processing your request...\n"
                    "1. ✅ Channel verified\n"
                    "2. Adding channel to database..."
                )

                # Store channel information
                stored_channel = channel_storage.add_channel(
                    user_id=message.from_user.id,
                    username=channel_username[1:],
                    title=channel.title
                )
                logger.info(f"Channel stored: {stored_channel}")

                await processing_msg.edit_text(
                    "⏳ Processing your request...\n"
                    "1. ✅ Channel verified\n"
                    "2. ✅ Channel added to database\n"
                    "3. Starting personality analysis...\n\n"
                    "🔄 This may take a few minutes. Please wait while I analyze the channel content..."
                )

                # Parse channel messages and analyze personality
                parsed_messages = await parser_service.parse_channel(channel_username)

                await processing_msg.edit_text(
                    "⏳ Processing your request...\n"
                    "1. ✅ Channel verified\n"
                    "2. ✅ Channel added to database\n"
                    "3. ✅ Messages collected\n"
                    "4. Generating personality profile...\n\n"
                    f"📊 Analyzing {len(parsed_messages)} messages..."
                )

                # Analyze personality
                personality = personality_analyzer.analyze_posts(parsed_messages)

                # Update storage with personality
                channel_storage.update_channel_personality(channel_username, personality)

                # Save personality to logs
                log_service.save_personality(channel_username, personality)

                # Log analysis results
                logger.info(
                    f"Personality analysis for {channel_username}:\n"
                    f"Traits: {', '.join(personality.traits)}\n"
                    f"Interests: {', '.join(personality.interests)}\n"
                    f"Communication Style: {personality.communication_style}"
                )

                # Delete processing message
                await processing_msg.delete()

                # Send final success message
                await message.reply(
                    f"""✨ Analysis complete!

Channel Profile for {channel_username}:

👤 Personality Traits:
{' • '.join([''] + personality.traits[:3])}

🎯 Main Interests:
{' • '.join([''] + personality.interests[:3])}

💬 Communication Style:
{personality.communication_style[:200]}...

📊 Analysis based on {len(parsed_messages)} messages

Use /list_channels to see all your channels
Use /add_wallet to link a wallet to this channel
                    """
                )

            except ValueError:
                await message.reply(
                    "❌ Channel not found!\n\n"
                    "Please check that:\n"
                    "1. The channel exists\n"
                    "2. The channel is public\n"
                    "3. You provided the correct username/link"
                )
            except Exception as e:
                logger.error(f"Error accessing channel: {e}", exc_info=True)
                await message.reply("❌ Sorry! I couldn't access that channel. Please try again later.")

        except Exception as e:
            logger.error(f"Error adding channel: {e}", exc_info=True)
            await message.reply("❌ An unexpected error occurred. Please try again later.")
        finally:
            await state.clear()

    @router.message(Command("add_wallet"))
    async def add_wallet(message: types.Message, state: FSMContext):
        # Get user's channels first
        channels = channel_storage.get_user_channels(message.from_user.id)

        if not channels:
            await message.reply(
                "❌ You don't have any channels yet!\n\n"
                "Please add a channel first using /add_channel"
            )
            return

        # Create inline keyboard with user's channels
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"@{channel.username}",
                        callback_data=f"select_channel:{channel.username}"  # Simple string format
                    )
                ] for channel in channels
            ]
        )

        await message.reply(
            "🔗 Select a channel to add a wallet:",
            reply_markup=keyboard
        )

    @router.callback_query(lambda c: c.data and c.data.startswith("select_channel:"))
    async def channel_selected(callback: types.CallbackQuery, state: FSMContext):
        try:
            # Extract channel username from callback data
            channel_username = callback.data.split(":")[-1]

            # Store selected channel in state
            await state.update_data(selected_channel=channel_username)
            await state.set_state(AddWallet.waiting_for_wallet)

            # Answer the callback to remove loading state
            await callback.answer()

            # Update message text
            await callback.message.edit_text(
                f"Selected channel: @{channel_username}\n\n"
                "💼 Please enter the wallet address now.\n\n"
                "Supported formats:\n"
                "• ETH: 0x...\n"
                "• SOL: ...\n"
                "• BTC: bc1...\n\n"
                "Type /cancel to abort"
            )
        except Exception as e:
            logger.error(f"Error in channel selection: {e}")
            await callback.answer("❌ Error processing selection", show_alert=True)

    @router.message(AddWallet.waiting_for_wallet)
    async def add_wallet_finish(message: types.Message, state: FSMContext):
        try:
            # Get the previously selected channel from state
            state_data = await state.get_data()
            channel_username = state_data.get('selected_channel')
            wallet_address = message.text.strip()

            # Basic wallet address validation
            if not wallet_address or len(wallet_address) < 26:  # minimum length for crypto addresses
                await message.reply(
                    "❌ Invalid wallet address!\n\n"
                    "Please provide a valid cryptocurrency wallet address"
                )
                return

            # Add wallet to storage
            wallet = channel_storage.add_wallet(channel_username, wallet_address)
            if wallet:
                await message.reply(
                    f"""✅ Wallet successfully added!

📢 Channel: @{channel_username}
💼 Wallet: `{wallet_address}`

Use /list_wallets @{channel_username} to see all wallets for this channel"""
                )
            else:
                await message.reply(
                    "❌ Failed to add wallet!\n\n"
                    f"Channel @{channel_username} not found. Please try again with /add_wallet"
                )

        except Exception as e:
            logger.error(f"Error adding wallet: {e}", exc_info=True)
            await message.reply("❌ An unexpected error occurred. Please try again.")
        finally:
            await state.clear()

    @router.message(Command("cancel"))
    async def cancel_operation(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
            await message.reply(
                "❌ Operation cancelled.\n\n"
                "Use /help to see available commands"
            )

    @router.message(Command("list_channels"))
    async def list_channels(message: types.Message):
        channels = channel_storage.get_user_channels(message.from_user.id)

        if not channels:
            await message.reply("You haven't added any channels yet! Use /add_channel to get started.")
            return

        response = "Your channels:\n\n"
        for channel in channels:
            response += f"📢 {channel.username}\n"
            response += f"Added: {channel.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            response += f"Wallets: {len(channel.wallets)}\n\n"

        await message.answer(response)

    @router.message(Command("list_wallets"))
    async def list_wallets(message: types.Message, state: FSMContext):
        await message.reply("Please provide a channel username")
        await state.set_state(WalletList.waiting_for_wallet_list)

    @router.message(WalletList.waiting_for_wallet_list)
    async def list_wallets_finish(message: types.Message, state: FSMContext):
        try:
            channel_username = await channel_service.cleanup_username(message.text)
            wallets = channel_storage.get_channel_wallets(channel_username)
            display_name = channel_username[1:] if channel_username.startswith('@') else channel_username

            if not wallets:
                await message.reply(f"No wallets found for {display_name}! Add one with /add_wallet {display_name} wallet_address")
                return

            response = f"Wallets for {display_name}:\n\n"
            for wallet in wallets:
                response += f"💼 {wallet.address}\n"
                response += f"Chain: {wallet.chain}\n"
                response += f"Added: {wallet.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"

            await message.answer(response)
        finally:
            await state.clear()