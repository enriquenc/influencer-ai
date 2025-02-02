from typing import Dict, Set, Optional, Callable
import threading
import queue
import time
import signal
from dataclasses import dataclass
from web3 import Web3
from onchain_parser.config import config
from onchain_parser.wallet_monitor import analyze_transaction, get_token_info, print_transaction_info

@dataclass
class WalletSubscription:
    address: str
    callback: Callable
    active: bool = True

class MonitorService:
    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(config.provider_url))
        self._subscriptions: Dict[str, WalletSubscription] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._event_queue = queue.Queue()
        self._shutdown_event = threading.Event()  # Add shutdown event

        # Set up signal handling
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C"""
        if self._shutdown_event.is_set():  # If already shutting down, force exit
            print("\nForce exiting...")
            exit(1)

        print("\nShutting down monitor gracefully...")
        self._shutdown_event.set()  # Signal shutdown
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)  # Wait max 5 seconds
        print("Monitor stopped.")
        exit(0)

    def subscribe(self, wallet_address: str, callback: Callable) -> bool:
        """Subscribe to a wallet's transactions"""
        with self._lock:
            wallet_address = wallet_address.lower()
            if wallet_address in self._subscriptions:
                return False

            self._subscriptions[wallet_address] = WalletSubscription(
                address=wallet_address,
                callback=callback
            )

            # Start monitor thread if not running
            if not self._running:
                self._start_monitor()

            return True

    def unsubscribe(self, wallet_address: str) -> bool:
        """Unsubscribe from a wallet's transactions"""
        with self._lock:
            wallet_address = wallet_address.lower()
            if wallet_address not in self._subscriptions:
                return False

            del self._subscriptions[wallet_address]

            # Stop monitor if no more subscriptions
            if not self._subscriptions and self._running:
                self._stop_monitor()

            return True

    def _start_monitor(self):
        """Start the background monitoring thread"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()

    def _stop_monitor(self):
        """Stop the background monitoring thread"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()
            self._monitor_thread = None

    def _monitor_loop(self):
        """Main monitoring loop"""
        last_block = self.web3.eth.block_number - 5
        print(f"Starting monitoring from block {last_block}")

        while self._running and not self._shutdown_event.is_set():
            try:
                current_block = self.web3.eth.block_number
                safe_block = current_block - 25
                chunk_size = 10

                if safe_block > last_block:
                    start_block = last_block + 1
                    end_block = min(safe_block, start_block + chunk_size)

                    for block_num in range(start_block, end_block):
                        if self._shutdown_event.is_set():  # Check for shutdown
                            return

                        max_retries = 5
                        retry_count = 0
                        block_processed = False

                        while retry_count < max_retries and not block_processed and not self._shutdown_event.is_set():
                            try:
                                # Get block with retries
                                block = None
                                for attempt in range(3):
                                    if self._shutdown_event.is_set():  # Check for shutdown
                                        return
                                    try:
                                        block = self.web3.eth.get_block(block_num, full_transactions=True)
                                        if block is not None:
                                            break
                                    except Exception as e:
                                        if attempt == 2:
                                            raise
                                        time.sleep(1)  # Reduced sleep time

                                if block is None:
                                    raise Exception(f"Failed to fetch block {block_num}")

                                if config.debug_mode:
                                    print(f"Processing block {block_num}")

                                # Get active subscriptions
                                with self._lock:
                                    active_subs = {
                                        addr: sub for addr, sub in self._subscriptions.items()
                                        if sub.active
                                    }

                                # Process transactions
                                for tx in block.transactions:
                                    if self._shutdown_event.is_set():  # Check for shutdown
                                        return

                                    tx_from = tx['from'].lower()
                                    tx_to = tx['to'].lower() if tx['to'] else None

                                    # Check each subscription
                                    for wallet_address, subscription in active_subs.items():
                                        if tx_from == wallet_address or tx_to == wallet_address:
                                            # Get transaction receipt with retries
                                            tx_receipt = None
                                            for attempt in range(5):
                                                if self._shutdown_event.is_set():  # Check for shutdown
                                                    return
                                                try:
                                                    tx_receipt = self.web3.eth.get_transaction_receipt(tx['hash'].hex())
                                                    if tx_receipt is not None:
                                                        break
                                                except Exception as e:
                                                    if attempt == 4:
                                                        raise
                                                    time.sleep(3 ** attempt)

                                            if tx_receipt is None:
                                                continue

                                            # Analyze and notify
                                            tx_event = analyze_transaction(tx, tx_receipt)
                                            if tx_event:
                                                print_transaction_info(tx_event)
                                                try:
                                                    subscription.callback(tx_event)
                                                except Exception as e:
                                                    print(f"Error in callback for {subscription.address}: {e}")

                                block_processed = True

                            except Exception as e:
                                if self._shutdown_event.is_set():  # Check for shutdown
                                    return
                                retry_count += 1
                                if retry_count >= max_retries:
                                    if config.debug_mode:
                                        print(f"Failed to process block {block_num} after {max_retries} attempts: {e}")
                                    break
                                if config.debug_mode:
                                    print(f"Error processing block {block_num} (attempt {retry_count}/{max_retries}): {e}")
                                time.sleep(1)  # Reduced sleep time

                        if block_processed or retry_count >= max_retries:
                            last_block = block_num

                        time.sleep(0.1)  # Reduced delay

                    time.sleep(0.5)  # Reduced delay

            except Exception as e:
                if self._shutdown_event.is_set():  # Check for shutdown
                    return
                if config.debug_mode:
                    print(f"Monitoring error: {e}")
                time.sleep(1)  # Reduced sleep time

            time.sleep(0.1)  # Reduced main loop delay

# Global monitor service instance
monitor_service = MonitorService()