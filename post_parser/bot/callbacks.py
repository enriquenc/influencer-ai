from typing import Optional
from aiogram.filters.callback_data import CallbackData

class ChannelAction(CallbackData, prefix="channel"):
    """Callback data for channel actions"""
    action: str
    username: str

    def pack(self) -> str:
        """Pack callback data into string"""
        return f"{self.prefix}:{self.action}:{self.username}"

    @classmethod
    def unpack(cls, value: str) -> dict:
        """Unpack callback data from string"""
        try:
            _, action, username = value.split(":")
            return {"action": action, "username": username}
        except ValueError:
            return {}