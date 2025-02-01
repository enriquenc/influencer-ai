from typing import Optional
from aiogram.filters.callback_data import CallbackData

class ChannelAction(CallbackData, prefix="channel"):
    """Callback data for channel actions"""
    action: str  # "generate_post", "approve_post"
    username: str