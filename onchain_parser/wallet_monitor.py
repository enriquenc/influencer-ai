from web3 import Web3
import requests
import json
from datetime import datetime
import time
from onchain_parser.config import config

# Connection to Base Mainnet using config
web3 = Web3(Web3.HTTPProvider(config.provider_url))

# Address to monitor from config
WALLET_ADDRESS = config.wallet_address
IGNORED_CONTRACTS = config.ignored_contracts

def get_token_info(token_address):
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
            return {
                'address': token_address,
                'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                'price': float(pair.get('priceUsd', 0)),
                'volume24h': float(pair.get('volume', {}).get('h24', 0)),
                'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                'priceChange24h': float(pair.get('priceChange', {}).get('h24', 0)),
            }
        return None
    except Exception as e:
        print(f"Error getting token info: {e}")
        return None

def analyze_transaction(transaction, tx_receipt):
    """Detailed transaction analysis"""
    try:
        # Calculate gas cost
        gas_cost_wei = tx_receipt['gasUsed'] * transaction['gasPrice']
        gas_cost_eth = web3.from_wei(gas_cost_wei, 'ether')

        # Get block for timestamp
        block = web3.eth.get_block(transaction['blockNumber'])

        # Analyze logs for Transfer events
        transfers = []
        processed_tokens = set()  # Track processed token addresses

        for log in tx_receipt['logs']:
            if len(log['topics']) == 3:
                try:
                    token_address = log['address']

                    from_addr = '0x' + log['topics'][1].hex()[-40:]
                    to_addr = '0x' + log['topics'][2].hex()[-40:]

                    # Check if sender or receiver matches transaction sender
                    if from_addr.lower() != transaction['from'].lower() and to_addr.lower() != transaction['from'].lower():
                        continue

                    # Skip if we already processed this token
                    if token_address.lower() in processed_tokens:
                        continue

                    # Determine operation type (buy/sell)
                    operation_type = 'SELL' if from_addr.lower() == transaction['from'].lower() else 'BUY'

                    # Get token info and price
                    token_info = get_token_info(token_address)

                    # Skip tokens without price on Dexscreener
                    if not token_info or token_info.get('price') is None:
                        continue

                    # Proper amount decoding
                    amount_hex = log['data']
                    if isinstance(amount_hex, bytes):
                        amount = int.from_bytes(amount_hex, 'big')
                    else:
                        amount = int(amount_hex, 16)

                    # Convert amount to proper format with decimals
                    try:
                        erc20_abi = [
                            {
                                "constant": True,
                                "inputs": [],
                                "name": "decimals",
                                "outputs": [{"name": "", "type": "uint8"}],
                                "type": "function"
                            }
                        ]
                        token_contract = web3.eth.contract(address=token_address, abi=erc20_abi)
                        decimals = token_contract.functions.decimals().call()
                        amount = amount / (10 ** decimals)
                    except:
                        # If failed to get decimals, leave as is
                        pass

                    transfers.append({
                        'token': token_info,
                        'from': from_addr,
                        'to': to_addr,
                        'amount': amount,
                        'operation': operation_type
                    })

                    # Mark this token as processed
                    processed_tokens.add(token_address.lower())

                except Exception as e:
                    print(f"Error processing log: {e}")
                    continue

        # If no matching transfers, return None
        if not transfers:
            return None

        return {
            'hash': transaction['hash'].hex(),
            'block_number': transaction['blockNumber'],
            'timestamp': block['timestamp'],
            'from': transaction['from'],
            'to': transaction['to'],
            'value': web3.from_wei(transaction['value'], 'ether'),
            'status': 'Success' if tx_receipt['status'] == 1 else 'Failed',
            'transfers': transfers
        }
    except Exception as e:
        print(f"Error analyzing transaction: {e}")
        return None

def print_transaction_info(tx_info):
    """Print transaction information"""
    print(f"""
═══════════════════════════════════════════════
New Transaction:
═══════════════════════════════════════════════
Time: {datetime.fromtimestamp(tx_info['timestamp'])}
Hash: {tx_info['hash']}
Block: {tx_info['block_number']}
Status: {tx_info['status']}

From: {tx_info['from']}
To: {tx_info['to']}
Value: {tx_info['value']} ETH
    """)

    if tx_info['transfers']:
        print("Token Information:")
        print("══════════════════════")

        for transfer in tx_info['transfers']:
            token = transfer['token']
            amount = transfer['amount']
            operation = transfer['operation']

            # Calculate total token value
            total_value = amount * token['price'] if token['price'] else None
            total_value_str = f"${total_value:.2f}" if total_value is not None else "No data"

            # Add operation emoji
            operation_emoji = "🔴" if operation == "SELL" else "🟢"

            print(f"""
{operation_emoji} Operation: {operation}
Token: {token['symbol']} ({token['address']})
└── Price: ${token['price']:.4f}
└── Price Change (24h): {token['priceChange24h']}%
└── Volume (24h): ${token['volume24h']:,.2f}
└── Liquidity: ${token['liquidity']:,.2f}
└── From: {transfer['from']}
└── To: {transfer['to']}
└── Amount: {amount}
└── Total Value: {total_value_str}
            """)

def monitor_transactions():
    """Transaction monitoring"""
    last_block = web3.eth.block_number
    print(f"Starting monitoring from block {last_block}")

    while True:
        try:
            current_block = web3.eth.block_number
            # Add confirmation buffer to avoid reorgs
            safe_block = current_block - 5  # Wait for 5 block confirmations

            if safe_block > last_block:
                for block_num in range(last_block + 1, safe_block + 1):
                    max_retries = 3
                    retry_count = 0

                    while retry_count < max_retries:
                        try:
                            block = web3.eth.get_block(block_num, full_transactions=True)
                            print(f"Checking block {block_num}")

                            for tx in block.transactions:
                                try:
                                    if tx['from'].lower() == WALLET_ADDRESS.lower() or \
                                       (tx['to'] and tx['to'].lower() == WALLET_ADDRESS.lower()):
                                        tx_receipt = web3.eth.get_transaction_receipt(tx['hash'].hex())
                                        if tx_receipt is None:
                                            print(f"Transaction receipt not found for {tx['hash'].hex()}, retrying...")
                                            time.sleep(1)
                                            continue

                                        tx_info = analyze_transaction(tx, tx_receipt)
                                        if tx_info:
                                            print_transaction_info(tx_info)
                                except Exception as e:
                                    print(f"Error processing transaction: {e}")
                                    continue

                            # Successfully processed block, break retry loop
                            break

                        except Exception as e:
                            retry_count += 1
                            if retry_count >= max_retries:
                                print(f"Failed to process block {block_num} after {max_retries} attempts: {e}")
                                break
                            print(f"Error processing block {block_num} (attempt {retry_count}/{max_retries}): {e}")
                            time.sleep(2 ** retry_count)  # Exponential backoff

                    # Update last_block only after successful processing or max retries exceeded
                    last_block = block_num

                    # Add delay between block requests to prevent rate limiting
                    time.sleep(config.block_delay)

        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(config.retry_delay)

        time.sleep(1)

if __name__ == "__main__":
    print("Starting transaction monitoring...")
    print(f"Monitored address: {WALLET_ADDRESS}")
    if config.debug_mode:
        print(f"Debug mode: enabled")
    monitor_transactions()