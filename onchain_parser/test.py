from onchain_parser.api import subscribe_to_wallet, unsubscribe_from_wallet
from onchain_parser.models import TransactionEvent
import time

# Test configuration
TEST_WALLET = "0xf4Aa85656D9350DaE3D8006D8Fb45c33415E6B21"
OUTPUT_FORMAT = "brief"  # or "full"

def transaction_callback(tx_event: TransactionEvent):
    """Example callback function"""
    if OUTPUT_FORMAT == 'full':
        print(tx_event.format_full())
    else:
        print(tx_event.format_brief())

def main():
    print(f"Starting monitor for wallet: {TEST_WALLET}")
    print(f"Output format: {OUTPUT_FORMAT}")
    print("Press Ctrl+C to stop...")

    # Subscribe to wallet
    if not subscribe_to_wallet(TEST_WALLET, transaction_callback):
        print("Failed to subscribe to wallet")
        return

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        unsubscribe_from_wallet(TEST_WALLET)

if __name__ == "__main__":
    main()