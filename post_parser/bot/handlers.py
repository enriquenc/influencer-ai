import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from telethon.tl.types import Channel
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError

from ..bot.states import AddChannel, AddWallet
from ..bot.responses import AIPersonality
from ..bot.callbacks import ChannelAction

logger = logging.getLogger(__name__)

def setup_handlers(
    router: Router,
    channel_storage,
    channel_service,
    parser_service,
    personality_analyzer,
    log_service,
    config: dict
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
        # Check if debug mode is enabled
        if config.get("debug_mode", False):
            debug_channel = config.get("debug_channel", "UkraineNow")
            logger.info(f"Debug mode enabled, adding default channel: {debug_channel}")
            try:
                # Send initial processing message
                processing_msg = await message.answer(
                    f"🔧 Debug Mode: Setting up default channel...\n"
                    f"1. Adding @{debug_channel}..."
                )

                # Add default debug channel
                stored_channel = channel_storage.add_channel(
                    user_id=message.from_user.id,
                    username=debug_channel,
                    title=f"{debug_channel} [Debug Channel]"
                )

                await processing_msg.edit_text(
                    f"🔧 Debug Mode: Setting up default channel...\n"
                    f"1. ✅ Channel added\n"
                    f"2. Starting personality analysis..."
                )

                # Parse and analyze channel messages
                parsed_messages = await parser_service.parse_channel(f"@{debug_channel}")

                await processing_msg.edit_text(
                    f"🔧 Debug Mode: Setting up default channel...\n"
                    f"1. ✅ Channel added\n"
                    f"2. ✅ Messages collected\n"
                    f"3. Generating personality profile..."
                )

                # Analyze personality
                personality = personality_analyzer.analyze_posts(parsed_messages)

                # Update storage with personality
                channel_storage.update_channel_personality(debug_channel, personality)

                # Save personality to logs
                log_service.save_personality(debug_channel, personality)

                # Delete processing message
                await processing_msg.delete()

                # Send welcome message with debug info
                await message.answer(
                    AIPersonality.WELCOME_MESSAGE +
                    f"\n\n🔧 Debug Mode: Default channel @{debug_channel} has been added!\n\n"
                    f"Channel Profile:\n"
                    f"👤 Personality Traits:\n"
                    f"{' • '.join([''] + personality.traits[:3])}\n\n"
                    f"🎯 Main Interests:\n"
                    f"{' • '.join([''] + personality.interests[:3])}\n\n"
                    f"💬 Communication Style:\n"
                    f"{personality.communication_style}\n\n"
                    f"📊 Analysis based on {len(parsed_messages)} messages"
                )

                logger.info(f"Debug channel added and analyzed: {stored_channel}")

            except Exception as e:
                logger.error(f"Error adding debug channel: {e}")
                await message.answer(
                    AIPersonality.WELCOME_MESSAGE +
                    f"\n\n❌ Debug Mode: Failed to add default channel @{debug_channel}."
                )
        else:
            await message.answer(
                AIPersonality.WELCOME_MESSAGE +
                "\n\nAvailable commands:\n"
                "/add_channel - Add a new channel\n"
                "/list_channels - View your channels\n"
                "/add_wallet - Add Base wallet to channel\n"
                "/generate_post - Generate test post for channel\n"
                "/help - Show this help message"
            )

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
{personality.communication_style}

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
        logger.info(f"Retrieved channels for user {message.from_user.id}: {channels}")

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
                        callback_data=f"select:{channel.username}"
                    )
                ] for channel in channels
            ]
        )
        logger.info("Created keyboard with buttons: " +
                   str([btn.callback_data for row in keyboard.inline_keyboard for btn in row]))

        await message.reply(
            "🔗 Select a channel to add a wallet:",
            reply_markup=keyboard
        )

    @router.callback_query(lambda c: c.data and c.data.startswith("select:"))
    async def channel_selected(callback: types.CallbackQuery, state: FSMContext):
        logger.info(f"Processing channel selection callback with data: {callback.data}")
        try:
            # Extract channel username from callback data
            channel_username = callback.data.split(":", 1)[1]
            logger.info(f"Extracted channel username: {channel_username}")

            # Store selected channel in state
            await state.update_data(selected_channel=channel_username)
            current_state = await state.get_state()
            logger.info(f"Current state before setting: {current_state}")

            await state.set_state(AddWallet.waiting_for_wallet)
            current_state = await state.get_state()
            logger.info(f"Current state after setting: {current_state}")

            # Answer the callback to remove loading state
            await callback.answer("Channel selected!")

            try:
                # Update message text
                await callback.message.edit_text(
                    f"Selected channel: @{channel_username}\n\n"
                    "💼 Please enter the Base wallet address.\n\n"
                    "Format:\n"
                    "• Base: 0x...\n\n"
                    "Type /cancel to abort"
                )
                logger.info("Successfully processed channel selection")
            except Exception as e:
                logger.error(f"Error updating message: {e}", exc_info=True)
                # Try sending a new message if editing fails
                await callback.message.answer(
                    f"Selected channel: @{channel_username}\n\n"
                    "💼 Please enter the Base wallet address.\n\n"
                    "Format:\n"
                    "• Base: 0x...\n\n"
                    "Type /cancel to abort"
                )
        except Exception as e:
            logger.error(f"Error in channel selection: {e}", exc_info=True)
            await callback.answer("❌ Error processing selection", show_alert=True)

    @router.message(AddWallet.waiting_for_wallet)
    async def add_wallet_finish(message: types.Message, state: FSMContext):
        try:
            # Get the previously selected channel from state
            state_data = await state.get_data()
            channel_username = state_data.get('selected_channel')
            wallet_address = message.text.strip()

            # Basic wallet address validation for Base (Ethereum format)
            if not wallet_address.startswith('0x') or len(wallet_address) != 42:
                await message.reply(
                    "❌ Invalid Base wallet address!\n\n"
                    "Please provide a valid Base wallet address starting with 0x"
                )
                return

            # Add wallet to storage with Base chain
            wallet = channel_storage.add_wallet(channel_username, wallet_address, chain="Base")
            if wallet:
                await message.reply(
                    f"""✅ Wallet successfully added!

📢 Channel: @{channel_username}
💼 Base Wallet: `{wallet_address}`

Use /list_channels to see all your channels and wallets"""
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
            await message.reply(
                "❌ You haven't added any channels yet!\n"
                "Use /add_channel to get started."
            )
            return

        response = "📊 Your Channels:\n\n"
        for channel in channels:
            response += f"📢 Channel: @{channel.username}\n"
            response += f"📅 Added: {channel.added_at.strftime('%Y-%m-%d %H:%M UTC')}\n"

            # Add bot permissions info
            response += "\n🤖 Bot Permissions:\n"
            permissions_info = await channel_service.get_permissions_info(channel.username)
            response += f"{permissions_info}\n"

            if channel.personality:
                response += "\n🧠 Personality:\n"
                response += f"• Traits: {', '.join(channel.personality.traits[:3])}\n"
                response += f"• Interests: {', '.join(channel.personality.interests[:3])}\n"
                response += f"• Style: {channel.personality.communication_style[:200]}...\n"

            if channel.wallets:
                response += "\n💼 Base Wallets:\n"
                for wallet in channel.wallets:
                    response += f"  • {wallet.address}\n"
                    response += f"    Added: {wallet.added_at.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                response += "\n💼 No wallets added yet\n"

            response += "\n" + "─" * 32 + "\n\n"

        # Add helpful commands at the bottom
        response += (
            "Commands:\n"
            "/add_channel - Add new channel\n"
            "/add_wallet - Add Base wallet to channel\n"
            "/generate_post - Generate test post for channel"
        )

        await message.answer(response)

    @router.message(Command("generate_post"))
    async def generate_post_start(message: types.Message):
        """Start the post generation process by showing channel selection"""
        channels = channel_storage.get_user_channels(message.from_user.id)

        if not channels:
            await message.reply(
                "❌ You haven't added any channels yet!\n"
                "Use /add_channel to get started."
            )
            return

        # Create inline keyboard with channels
        builder = InlineKeyboardBuilder()
        for channel in channels:
            builder.button(
                text=f"@{channel.username}",
                callback_data=ChannelAction(
                    action="generate_post",
                    username=channel.username
                ).pack()
            )
        builder.adjust(1)  # One button per row

        await message.reply(
            "🎯 Select a channel to generate a test post:",
            reply_markup=builder.as_markup()
        )

    @router.callback_query(ChannelAction.filter(F.action == "generate_post"))
    async def generate_post_callback(
        query: types.CallbackQuery,
        callback_data: ChannelAction
    ):
        """Handle channel selection for post generation"""
        channel_username = callback_data.username
        channel = channel_storage.get_channel(channel_username)

        if not channel or not channel.personality:
            await query.message.edit_text(
                "❌ Channel personality not found. Please analyze the channel first using /add_channel"
            )
            return

        try:
            # Use personality_analyzer from closure
            post = personality_analyzer.generate_post(
                personality=channel.personality
            )

            # Create approve/regenerate keyboard
            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ Approve & Post",
                callback_data=ChannelAction(
                    action="approve_post",
                    username=channel_username
                ).pack()
            )
            builder.button(
                text="🔄 Regenerate",
                callback_data=ChannelAction(
                    action="generate_post",
                    username=channel_username
                ).pack()
            )
            builder.adjust(2)  # Two buttons in one row

            # Show personality traits used for generation
            await query.message.edit_text(
                f"📝 Generated post for @{channel_username}\n"
                f"Based on:\n"
                f"• Traits: {', '.join(channel.personality.traits[:3])}\n"
                f"• Interests: {', '.join(channel.personality.interests[:3])}\n"
                f"• Style: {channel.personality.communication_style[:100]}...\n\n"
                f"Generated Post:\n"
                f"{'─' * 32}\n"
                f"{post}\n"
                f"{'─' * 32}\n\n"
                "What would you like to do?",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            logger.error(f"Error generating post: {e}", exc_info=True)
            await query.message.edit_text(
                "❌ Failed to generate post. Please try again later."
            )

    @router.callback_query(ChannelAction.filter(F.action == "approve_post"))
    async def approve_post_callback(
        query: types.CallbackQuery,
        callback_data: ChannelAction
    ):
        """Handle post approval and publishing"""
        try:
            # Extract just the post content between the separator lines
            message_parts = query.message.text.split('─' * 32)
            if len(message_parts) >= 3:
                # Get the content between the separator lines
                post_text = message_parts[1].strip()
            else:
                raise ValueError("Could not extract post content")

            # Use channel_service from closure
            await channel_service.send_message(
                channel_username=callback_data.username,
                message=post_text
            )

            await query.message.edit_text(
                f"✅ Post successfully published to @{callback_data.username}!"
            )

        except ChatAdminRequiredError as e:
            await query.message.edit_text(
                f"❌ Cannot post to @{callback_data.username}\n\n"
                f"{str(e)}\n\n"
                "Please add the required permissions and try again."
            )
        except ChannelPrivateError:
            await query.message.edit_text(
                f"❌ Cannot access @{callback_data.username}\n\n"
                "The channel is private or the bot has no access.\n"
                "Please make sure the bot is a member of the channel."
            )
        except Exception as e:
            logger.error(f"Error publishing post: {e}", exc_info=True)
            await query.message.edit_text(
                "❌ Failed to publish post. Please try again later."
            )

    @router.message(Command("help"))
    async def cmd_help(message: types.Message):
        help_text = (
            "🤖 Available Commands:\n\n"
            "📢 Channel Management:\n"
            "/add_channel - Add a new channel\n"
            "/list_channels - View your channels\n"
            "/generate_post - Generate test post for channel\n\n"
            "💼 Wallet Management:\n"
            "/add_wallet - Add Base wallet to channel\n\n"
            "ℹ️ Other:\n"
            "/help - Show this help message\n"
            "/cancel - Cancel current operation"
        )
        await message.answer(help_text)