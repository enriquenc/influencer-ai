from typing import Callable
from onchain_parser.monitor_service import monitor_service

def subscribe_to_wallet(wallet_address: str, callback: Callable) -> bool:
    """
    Subscribe to a wallet's transactions

    Args:
        wallet_address: The wallet address to monitor
        callback: Function to be called when a transaction is detected
                 Callback signature: fn(transaction_info: dict)

    Returns:
        bool: True if subscription was successful
    """
    return monitor_service.subscribe(wallet_address, callback)

def unsubscribe_from_wallet(wallet_address: str) -> bool:
    """
    Unsubscribe from a wallet's transactions

    Args:
        wallet_address: The wallet address to stop monitoring

    Returns:
        bool: True if unsubscription was successful
    """
    return monitor_service.unsubscribe(wallet_address)