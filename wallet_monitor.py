from web3 import Web3
from dotenv import load_dotenv
import os
import requests
import json
from eth_utils import to_checksum_address
from datetime import datetime
from decimal import Decimal
import time

# Load environment variables
load_dotenv()

# Configuration
RPC_URL = os.getenv('RPC_URL')
WALLET_ADDRESS = os.getenv('YOUR_WALLET_ADDRESS')
DEXSCREENER_API = "https://api.dexscreener.com/latest"
CHAIN_NAME = "base"  # Network name for DexScreener

# Path to JSON file
JSON_FILE = "wallet_data.json"

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Standard ABI for ERC20 tokens
ERC20_ABI = json.loads('''[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}
]''')

def get_token_price(token_address):
    """Get token price from DexScreener API"""
    try:
        url = f"{DEXSCREENER_API}/dex/tokens/{token_address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            # Filter pairs only for Base network
            base_pairs = [p for p in pairs if p.get('chainId') == CHAIN_NAME]
            if base_pairs:
                # Get price from pair with highest volume
                sorted_pairs = sorted(base_pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)), reverse=True)
                return float(sorted_pairs[0].get('priceUsd', 0))
        return 0
    except:
        return 0

def get_eth_price():
    """Get ETH price from DexScreener API"""
    try:
        # Use WETH address for Base
        weth_address = "0x4200000000000000000000000000000000000006"
        url = f"{DEXSCREENER_API}/dex/tokens/{weth_address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            base_pairs = [p for p in pairs if p.get('chainId') == CHAIN_NAME]
            if base_pairs:
                sorted_pairs = sorted(base_pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)), reverse=True)
                return float(sorted_pairs[0].get('priceUsd', 0))
        return 0
    except:
        return 0

def get_token_info(token_address):
    """Get token information"""
    try:
        token_contract = web3.eth.contract(address=to_checksum_address(token_address), abi=ERC20_ABI)
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        balance = token_contract.functions.balanceOf(WALLET_ADDRESS).call()
        balance_formatted = float(balance) / (10 ** decimals)
        
        # Get additional information from DexScreener
        dex_info = {}
        try:
            url = f"{DEXSCREENER_API}/dex/tokens/{token_address}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                base_pairs = [p for p in pairs if p.get('chainId') == CHAIN_NAME]
                if base_pairs:
                    sorted_pairs = sorted(base_pairs, key=lambda x: float(x.get('volume', {}).get('h24', 0)), reverse=True)
                    best_pair = sorted_pairs[0]
                    dex_info = {
                        'volume_24h': best_pair.get('volume', {}).get('h24', '0'),
                        'price_change_24h': best_pair.get('priceChange', {}).get('h24', '0'),
                        'liquidity_usd': best_pair.get('liquidity', {}).get('usd', '0'),
                        'dex_id': best_pair.get('dexId', 'unknown')
                    }
        except:
            pass
        
        return {
            'symbol': symbol,
            'balance': balance_formatted,
            'decimals': decimals,
            **dex_info
        }
    except:
        return None

def get_wallet_tokens():
    """Get list of tokens in wallet"""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenBalances",
            "params": [WALLET_ADDRESS]
        }
        response = requests.post(RPC_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                token_balances = data['result'].get('tokenBalances', [])
                return [tb['contractAddress'] for tb in token_balances if int(tb['tokenBalance'], 16) > 0]
        return []
    except:
        return []

def get_eth_balance():
    """Get ETH balance"""
    try:
        balance_wei = web3.eth.get_balance(WALLET_ADDRESS)
        return float(web3.from_wei(balance_wei, 'ether'))
    except:
        return 0

def save_to_json(data):
    """Save data to JSON file"""
    try:
        # Read existing data if file exists
        history = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as f:
                history = json.load(f)
        
        # Add new data
        history.append(data)
        
        # Keep only last 100 records
        if len(history) > 100:
            history = history[-100:]
        
        # Write updated data
        with open(JSON_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving JSON: {e}")

def scan_wallet():
    """Scan wallet and display portfolio"""
    print(f"\nScanning wallet: {WALLET_ADDRESS}")
    print("\n" + "="*50)
    
    # Create dictionary for data storage
    wallet_data = {
        'timestamp': datetime.now().isoformat(),
        'wallet_address': WALLET_ADDRESS,
        'total_value_usd': 0.0,
        'eth': {},
        'tokens': [],
        'stats': {
            'valid_tokens': 0,
            'skipped_tokens': 0
        }
    }
    
    # Get and display ETH balance
    eth_balance = get_eth_balance()
    eth_price = get_eth_price()
    eth_value = float(eth_balance) * float(eth_price)
    
    if eth_value >= 1:  # Show ETH only if value >= 1 USD
        wallet_data['total_value_usd'] += eth_value
        wallet_data['eth'] = {
            'balance': eth_balance,
            'price': eth_price,
            'value': eth_value
        }
        print(f"\nETH Balance: {eth_balance:.4f} ETH")
        print(f"ETH Price: ${eth_price:.2f}")
        print(f"ETH Value: ${eth_value:.2f}")
        print("-"*50)
    
    # Get list of tokens
    print("\nScanning tokens...")
    token_addresses = get_wallet_tokens()
    
    # Get information about each token
    valid_tokens = 0
    skipped_tokens = 0
    
    for token_address in token_addresses:
        try:
            token_info = get_token_info(token_address)
            if not token_info:
                skipped_tokens += 1
                continue
                
            token_price = get_token_price(token_address)
            token_value = float(token_info['balance']) * float(token_price)
            
            # Skip tokens worth less than 1 USD
            if token_value < 1:
                skipped_tokens += 1
                continue
                
            wallet_data['total_value_usd'] += token_value
            valid_tokens += 1
            
            # Save token information
            token_data = {
                'address': token_address,
                'symbol': token_info['symbol'],
                'balance': token_info['balance'],
                'price': token_price,
                'value': token_value
            }
            
            # Add additional information if available
            if token_info.get('volume_24h', '0') != '0':
                token_data['volume_24h'] = float(token_info['volume_24h'])
            if token_info.get('price_change_24h'):
                token_data['price_change_24h'] = token_info['price_change_24h']
            if token_info.get('liquidity_usd', '0') != '0':
                token_data['liquidity_usd'] = float(token_info['liquidity_usd'])
            if token_info.get('dex_id') and token_info['dex_id'] != 'unknown':
                token_data['dex_id'] = token_info['dex_id']
            
            wallet_data['tokens'].append(token_data)
            
            # Display information
            print(f"\nToken: {token_info['symbol']}")
            print(f"Balance: {token_info['balance']:.4f}")
            print(f"Price: ${token_price:.4f}")
            print(f"Value: ${token_value:.2f}")
            
            if token_info.get('volume_24h', '0') != '0':
                print(f"24h Volume: ${float(token_info['volume_24h']):,.2f}")
            if token_info.get('price_change_24h'):
                print(f"24h Price Change: {token_info['price_change_24h']}%")
            if token_info.get('liquidity_usd', '0') != '0':
                print(f"Liquidity: ${float(token_info['liquidity_usd']):,.2f}")
            if token_info.get('dex_id') and token_info['dex_id'] != 'unknown':
                print(f"DEX: {token_info['dex_id']}")
            print("-"*50)
        except:
            skipped_tokens += 1
            continue
    
    # Update statistics
    wallet_data['stats']['valid_tokens'] = valid_tokens
    wallet_data['stats']['skipped_tokens'] = skipped_tokens
    
    # Save data to JSON
    save_to_json(wallet_data)
    
    print("\n" + "="*50)
    print(f"Total Portfolio Value: ${wallet_data['total_value_usd']:.2f}")
    print(f"Valid Tokens: {valid_tokens}")
    print(f"Skipped Tokens: {skipped_tokens}")
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

if __name__ == "__main__":
    if not web3.is_connected():
        print("Error: Could not connect to network")
        exit(1)
    
    try:
        while True:
            scan_wallet()
            user_input = input("\nPress Enter to update or 'q' to quit: ")
            if user_input.lower() == 'q':
                break
            time.sleep(1)  # Small delay between updates
    except KeyboardInterrupt:
        print("\nProgram terminated by user") 