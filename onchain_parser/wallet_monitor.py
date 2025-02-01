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

def get_token_price(token_address):
    """Get token price from Dexscreener"""
    # List of stablecoins
    stablecoins = {
        '0x036CbD53842c5426634e7929541eC2318f3dCF7e'.lower(): 1.0,  # USDC Base
        '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'.lower(): 1.0,  # USDT Base
        # Add other USDC/USDT addresses if needed
    }

    # Check if token is a stablecoin
    if token_address.lower() in stablecoins:
        return stablecoins[token_address.lower()]

    # If not, get price from Dexscreener
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('pairs'):
            return float(data['pairs'][0]['priceUsd'])
        return None
    except Exception as e:
        print(f"Error getting price: {e}")
        return None

def get_token_info(token_address):
    """Get token information"""
    try:
        # Basic ERC20 ABI to get token symbol
        erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]
        token_contract = web3.eth.contract(address=token_address, abi=erc20_abi)
        symbol = token_contract.functions.symbol().call()
        price = get_token_price(token_address)
        return {
            'address': token_address,
            'symbol': symbol,
            'price': price
        }
    except Exception as e:
        return {
            'address': token_address,
            'symbol': 'UNKNOWN',
            'price': None
        }

def analyze_transaction(transaction, tx_receipt):
    """Detailed transaction analysis"""
    try:
        # Calculate gas cost
        gas_cost_wei = tx_receipt['gasUsed'] * transaction['gasPrice']
        gas_cost_eth = web3.from_wei(gas_cost_wei, 'ether')

        # Get block for timestamp
        block = web3.eth.get_block(transaction['blockNumber'])

        # Check if this is a contract interaction
        input_data = transaction.get('input', '0x')
        is_contract_interaction = input_data != '0x'

        # Analyze logs for Transfer events
        transfers = []
        for log in tx_receipt['logs']:
            # Check for both ERC20 transfers (3 topics) and other events
            if len(log['topics']) >= 1:
                try:
                    token_address = log['address']

                    # Skip ignored contracts from config
                    if token_address.lower() in IGNORED_CONTRACTS:
                        continue

                    # For standard ERC20 transfers
                    if len(log['topics']) == 3:
                        from_addr = '0x' + log['topics'][1].hex()[-40:]
                        to_addr = '0x' + log['topics'][2].hex()[-40:]
                    else:
                        # For other types of transfers/events
                        from_addr = transaction['from']
                        to_addr = transaction['to']

                    # Proper amount decoding
                    amount_hex = log['data']
                    if isinstance(amount_hex, bytes):
                        amount = int.from_bytes(amount_hex, 'big')
                    else:
                        amount = int(amount_hex, 16)

                    token_info = get_token_info(token_address)

                    # Convert amount to proper format considering decimals
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
                        # If unable to get decimals, leave as is
                        pass

                    transfers.append({
                        'token': token_info,
                        'from': from_addr,
                        'to': to_addr,
                        'amount': amount,
                        'is_contract_interaction': is_contract_interaction
                    })
                except Exception as e:
                    print(f"Error processing log: {e}")
                    continue

        return {
            'hash': transaction['hash'].hex(),
            'block_number': transaction['blockNumber'],
            'timestamp': block['timestamp'],
            'from': transaction['from'],
            'to': transaction['to'],
            'value': web3.from_wei(transaction['value'], 'ether'),
            'gas_price': web3.from_wei(transaction['gasPrice'], 'gwei'),
            'gas_used': tx_receipt['gasUsed'],
            'gas_cost_eth': gas_cost_eth,
            'status': 'Success' if tx_receipt['status'] == 1 else 'Failed',
            'transfers': transfers,
            'is_contract_interaction': is_contract_interaction,
            'input_data': input_data if is_contract_interaction else None
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

Gas:
----
Used: {tx_info['gas_used']}
Gas Price: {tx_info['gas_price']} Gwei
Total Cost: {tx_info['gas_cost_eth']} ETH
    """)

    if tx_info['is_contract_interaction']:
        print(f"Contract Interaction: Yes")
        if config.debug_mode:
            print(f"Input Data: {tx_info['input_data']}")

    if tx_info['transfers']:
        print("Token Information:")
        print("══════════════════════")

        for transfer in tx_info['transfers']:
            token = transfer['token']
            amount = transfer['amount']
            price = token['price']

            # Calculate total token value
            total_value = amount * price if price is not None else None
            total_value_str = f"${total_value:.2f}" if total_value is not None else "No data"

            print(f"""
Token: {token['symbol']} ({token['address']})
└── Price: ${token['price'] if token['price'] else 'No data'}
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
            if current_block > last_block:
                for block_num in range(last_block + 1, current_block + 1):
                    try:
                        block = web3.eth.get_block(block_num, full_transactions=True)
                        print(f"Checking block {block_num}")

                        for tx in block.transactions:
                            if tx['from'].lower() == WALLET_ADDRESS.lower() or \
                               (tx['to'] and tx['to'].lower() == WALLET_ADDRESS.lower()):
                                tx_receipt = web3.eth.get_transaction_receipt(tx['hash'].hex())
                                tx_info = analyze_transaction(tx, tx_receipt)
                                if tx_info:
                                    print_transaction_info(tx_info)

                        # Update last_block only after successful processing
                        last_block = block_num

                        # Add delay between block requests to prevent rate limiting
                        time.sleep(config.block_delay)

                    except Exception as e:
                        print(f"Error processing block {block_num}: {e}")
                        # Don't update last_block if block not found
                        # This ensures we'll try this block again
                        break  # Exit the loop to retry from this block

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