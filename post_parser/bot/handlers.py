import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from telethon.tl.types import Channel

from ..bot.states import AddChannel, AddWallet, WalletList
from ..bot.responses import AIPersonality

def setup_handlers(
    router: Router,
    channel_storage,
    channel_service,
    parser_service
) -> None:
    """Setup all bot command handlers"""

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
            logging.info(f"Received channel username: {channel_username}")

            # Format check and conversion
            if channel_username.startswith('https://t.me/'):
                channel_username = await channel_service.cleanup_username(channel_username)
            elif not channel_username.startswith('@'):
                await message.reply("Please provide a valid channel username starting with @ or a t.me link")
                return

            try:
                channel = await channel_service.get_channel_entity(channel_username)
                logging.info(f"Channel info retrieved: {channel}")

                # Store channel information
                stored_channel = channel_storage.add_channel(
                    user_id=message.from_user.id,
                    username=channel_username[1:],
                    title=channel.title
                )
                logging.info(f"Channel stored: {stored_channel}")

                await message.reply(AIPersonality.channel_added(channel_username))

                # Parse channel messages
                await parse_channel_messages(message, channel_username, parser_service)

            except ValueError as ve:
                await message.reply(
                    f"Could not find channel {channel_username}.\n"
                    "Please make sure:\n"
                    "1. The channel exists\n"
                    "2. The channel is public\n"
                    "3. You provided the correct username/link"
                )
                logging.error(f"Channel not found: {ve}")
            except Exception as e:
                await message.reply(f"Error accessing channel: {str(e)}")
                logging.error(f"Error getting channel info: {e}", exc_info=True)

        except Exception as e:
            logging.error(f"Error adding channel: {str(e)}", exc_info=True)
            await message.reply(f"Sorry! 😅 I couldn't add that channel. Error: {str(e)}")
        finally:
            await state.clear()

    @router.message(Command("add_wallet"))
    async def add_wallet(message: types.Message, state: FSMContext):
        await message.reply("Please provide a channel username and wallet address")
        await state.set_state(AddWallet.waiting_for_wallet)

    @router.message(AddWallet.waiting_for_wallet)
    async def add_wallet_finish(message: types.Message, state: FSMContext):
        try:
            command_parts = message.text.split()
            if len(command_parts) < 2:
                await message.answer("Please provide channel username and wallet address")
                return

            channel_username = await channel_service.cleanup_username(command_parts[0])
            wallet_address = command_parts[1]

            wallet = channel_storage.add_wallet(channel_username, wallet_address)
            if wallet:
                await message.reply(AIPersonality.wallet_added(channel_username, wallet_address))
            else:
                await message.reply(f"Channel {channel_username} not found! Add it first with /add_channel {channel_username}")
        finally:
            await state.clear()

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

async def parse_channel_messages(message: types.Message, channel_username: str, parser_service):
    """Parse and analyze channel messages"""
    try:
        parsed_messages = await parser_service.parse_channel(channel_username)
        await message.answer(
            f"""✨ Analysis complete! I've processed {len(parsed_messages)} posts from {channel_username}.

The data has been saved and I'm ready to provide insights about your content!
            """
        )
    except Exception as e:
        await message.answer(f"Oops! 😅 Something went wrong while parsing messages: {str(e)}")