from web3 import Web3
import requests
import json
from datetime import datetime
import time
from onchain_parser.config import config
from onchain_parser.models import TransactionEvent, TokenTransfer, TokenInfo
from typing import Optional
import logging

# Connection to Base Mainnet using config
web3 = Web3(Web3.HTTPProvider(config.provider_url))

# Address to monitor from config
WALLET_ADDRESS = config.wallet_address
IGNORED_CONTRACTS = config.ignored_contracts

# Configure logger
logger = logging.getLogger(__name__)

def get_token_info(token_address) -> Optional[TokenInfo]:
    """Get token information from Dexscreener"""
    try:
        # Check for WETH address
        if token_address.lower() == '0x0a2854Fbbd9B3Ef66F17d47284E7f899b9509330'.lower():
            token_address = '0x4200000000000000000000000000000000000006'  # Base WETH

        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url)
        data = response.json()

        if data.get('pairs'):
            pair = data['pairs'][0]  # Get first pair as main
            return TokenInfo(
                address=token_address,
                symbol=pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                price=float(pair.get('priceUsd', 0)),
                volume24h=float(pair.get('volume', {}).get('h24', 0)),
                liquidity=float(pair.get('liquidity', {}).get('usd', 0)),
                priceChange24h=float(pair.get('priceChange', {}).get('h24', 0))
            )
        return None
    except Exception as e:
        print(f"Error getting token info: {e}")
        return None

def analyze_transaction(transaction, tx_receipt) -> Optional[TransactionEvent]:
    """Detailed transaction analysis"""
    try:
        # Get block with retries
        block = None
        for attempt in range(3):
            try:
                block = web3.eth.get_block(transaction['blockNumber'])
                if block is not None:
                    break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Failed to get block {transaction['blockNumber']}: {e}")
                    raise
                time.sleep(1)

        if block is None:
            raise Exception(f"Could not fetch block {transaction['blockNumber']}")

        # Log transaction details for debugging
        logger.info(f"Analyzing transaction: {transaction['hash'].hex()}")
        logger.info(f"From: {transaction['from']}")
        logger.info(f"To: {transaction['to']}")
        logger.info(f"Value: {web3.from_wei(transaction['value'], 'ether')} ETH")

        # Calculate gas cost
        gas_cost_wei = tx_receipt['gasUsed'] * transaction['gasPrice']
        gas_cost_eth = web3.from_wei(gas_cost_wei, 'ether')

        # Analyze logs for Transfer events
        transfers = []
        processed_tokens = set()

        for log in tx_receipt['logs']:
            try:
                if len(log['topics']) == 3:  # Standard ERC20 Transfer event
                    token_address = log['address']

                    # Skip if already processed
                    if token_address.lower() in processed_tokens:
                        continue

                    from_addr = '0x' + log['topics'][1].hex()[-40:]
                    to_addr = '0x' + log['topics'][2].hex()[-40:]

                    # Log transfer details for debugging
                    logger.debug(f"Found transfer: {from_addr} -> {to_addr}")

                    # Check if sender or receiver matches transaction sender
                    if from_addr.lower() != transaction['from'].lower() and to_addr.lower() != transaction['from'].lower():
                        continue

                    # Get token info with retries
                    token_info = None
                    for attempt in range(3):
                        try:
                            token_info = get_token_info(token_address)
                            if token_info:
                                break
                        except Exception as e:
                            if attempt == 2:
                                logger.error(f"Failed to get token info for {token_address}: {e}")
                            time.sleep(1)

                    if not token_info:
                        continue

                    # Process amount with better error handling
                    try:
                        amount_hex = log['data']
                        if isinstance(amount_hex, bytes):
                            amount = int.from_bytes(amount_hex, 'big')
                        else:
                            amount = int(amount_hex, 16)

                        # Get token decimals (default to 18 if not available)
                        token_decimals = 18  # Most ERC20 tokens use 18 decimals
                        try:
                            # Create contract instance to get decimals
                            contract = web3.eth.contract(
                                address=token_address,
                                abi=[{
                                    "constant": True,
                                    "inputs": [],
                                    "name": "decimals",
                                    "outputs": [{"name": "", "type": "uint8"}],
                                    "type": "function"
                                }]
                            )
                            token_decimals = contract.functions.decimals().call()
                        except Exception as e:
                            logger.warning(f"Could not get token decimals, using default 18: {e}")

                        # Convert raw amount to actual amount using decimals
                        actual_amount = amount / (10 ** token_decimals)

                        # Log successful transfer processing
                        logger.info(f"Processed transfer of {token_info.symbol}: {actual_amount} (raw: {amount}, decimals: {token_decimals})")

                        transfers.append(TokenTransfer(
                            token=token_info,
                            from_address=from_addr,
                            to_address=to_addr,
                            amount=actual_amount,  # Use the converted amount
                            operation='SELL' if from_addr.lower() == transaction['from'].lower() else 'BUY'
                        ))
                        processed_tokens.add(token_address.lower())
                    except Exception as e:
                        logger.error(f"Error processing transfer amount: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error processing log entry: {e}")
                continue

        # Create and return transaction event
        tx_event = TransactionEvent(
            hash=transaction['hash'].hex(),
            block_number=transaction['blockNumber'],
            timestamp=block['timestamp'],
            from_address=transaction['from'],
            to_address=transaction['to'],
            value=web3.from_wei(transaction['value'], 'ether'),
            status='Success' if tx_receipt['status'] == 1 else 'Failed',
            transfers=transfers
        )

        # Log successful analysis
        logger.info(f"Successfully analyzed transaction {tx_event.hash}")
        return tx_event

    except Exception as e:
        logger.error(f"Error analyzing transaction {transaction['hash'].hex()}: {e}", exc_info=True)
        return None

def print_transaction_info(tx_event: TransactionEvent):
    """Print transaction information"""
    print(tx_event.format_full())

def monitor_transactions():
    """Transaction monitoring"""
    last_block = web3.eth.block_number - 10  # Start from 50 blocks behind to ensure stability
    print(f"Starting monitoring from block {last_block}")

    while True:
        try:
            current_block = web3.eth.block_number
            # Increase buffer and process smaller chunks
            safe_block = current_block - 25  # Wait for 25 block confirmations
            chunk_size = 10  # Process blocks in smaller chunks

            if safe_block > last_block:
                # Process blocks in chunks to avoid overwhelming the RPC
                start_block = last_block + 1
                end_block = min(safe_block, start_block + chunk_size)

                for block_num in range(start_block, end_block):
                    max_retries = 5
                    retry_count = 0
                    block_processed = False

                    while retry_count < max_retries and not block_processed:
                        try:
                            # Add retry logic for block fetching with longer timeouts
                            block = None
                            for attempt in range(3):
                                try:
                                    block = web3.eth.get_block(block_num, full_transactions=True)
                                    if block is not None:
                                        break
                                except Exception as e:
                                    if attempt == 2:
                                        raise
                                    time.sleep(3 ** attempt)  # Increased exponential backoff

                            if block is None:
                                raise Exception(f"Failed to fetch block {block_num}")

                            if config.debug_mode:
                                print(f"Processing block {block_num}")

                            # Process transactions in the block
                            for tx in block.transactions:
                                if tx['from'].lower() == WALLET_ADDRESS.lower() or \
                                   (tx['to'] and tx['to'].lower() == WALLET_ADDRESS.lower()):

                                    # Enhanced retry logic for transaction receipt
                                    tx_receipt = None
                                    receipt_retries = 5
                                    for attempt in range(receipt_retries):
                                        try:
                                            tx_receipt = web3.eth.get_transaction_receipt(tx['hash'].hex())
                                            if tx_receipt is not None:
                                                break
                                        except Exception as e:
                                            if attempt == receipt_retries - 1:
                                                raise
                                            time.sleep(3 ** attempt)  # Increased backoff delay

                                    if tx_receipt is None:
                                        continue

                                    tx_info = analyze_transaction(tx, tx_receipt)
                                    if tx_info:
                                        print_transaction_info(tx_info)

                            block_processed = True  # Mark block as successfully processed

                        except Exception as e:
                            retry_count += 1
                            if retry_count >= max_retries:
                                if config.debug_mode:
                                    print(f"Failed to process block {block_num} after {max_retries} attempts: {e}")
                                break
                            if config.debug_mode:
                                print(f"Error processing block {block_num} (attempt {retry_count}/{max_retries}): {e}")
                            time.sleep(3 ** retry_count)  # Increased exponential backoff

                    # Update last_block if block was processed or max retries reached
                    if block_processed or retry_count >= max_retries:
                        last_block = block_num

                    # Add delay between blocks to prevent rate limiting
                    time.sleep(config.block_delay * 2)

                # Add extra delay between chunks
                time.sleep(config.block_delay * 3)

        except Exception as e:
            if config.debug_mode:
                print(f"Monitoring error: {e}")
            time.sleep(config.retry_delay * 2)

        time.sleep(3)  # Increased main loop delay

if __name__ == "__main__":
    print("Starting transaction monitoring...")
    print(f"Monitored address: {WALLET_ADDRESS}")
    if config.debug_mode:
        print(f"Debug mode: enabled")
    monitor_transactions()