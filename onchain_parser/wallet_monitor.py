from web3 import Web3
import requests
import json
from datetime import datetime
import time

# Подключение к Base Sepolia
WEB3_PROVIDER = "https://base-mainnet.g.alchemy.com/v2/{api_key}"
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# Адрес для отслеживания
WALLET_ADDRESS = "0x939d8f09e002EaF17E10acaB804164becE5B8e3c"

def get_token_price(token_address):
    """Получение цены токена с Dexscreener"""
    # Список стейблкоинов
    stablecoins = {
        '0x036CbD53842c5426634e7929541eC2318f3dCF7e'.lower(): 1.0,  # USDC Base
        '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'.lower(): 1.0,  # USDT Base
        # Добавьте другие адреса USDC/USDT если нужно
    }
    
    # Проверяем, является ли токен стейблкоином
    if token_address.lower() in stablecoins:
        return stablecoins[token_address.lower()]
        
    # Если нет, получаем цену с Dexscreener
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('pairs'):
            return float(data['pairs'][0]['priceUsd'])
        return None
    except Exception as e:
        print(f"Ошибка при получении цены: {e}")
        return None

def get_token_info(token_address):
    """Получение информации о токене"""
    try:
        # Базовый ERC20 ABI для получения символа токена
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
    """Детальный анализ транзакции"""
    try:
        # Расчет стоимости газа
        gas_cost_wei = tx_receipt['gasUsed'] * transaction['gasPrice']
        gas_cost_eth = web3.from_wei(gas_cost_wei, 'ether')
        
        # Получаем блок для временной метки
        block = web3.eth.get_block(transaction['blockNumber'])
        
        # Анализ логов для поиска Transfer событий
        transfers = []
        for log in tx_receipt['logs']:
            if len(log['topics']) == 3:
                try:
                    token_address = log['address']
                    
                    # Пропускаем указанный токен контракт
                    if token_address.lower() == '0x45383e82f90Ff65391102D460B34E75030b0eB2b'.lower():
                        continue
                        
                    from_addr = '0x' + log['topics'][1].hex()[-40:]
                    to_addr = '0x' + log['topics'][2].hex()[-40:]
                    
                    # Правильное декодирование amount
                    amount_hex = log['data']
                    if isinstance(amount_hex, bytes):
                        amount = int.from_bytes(amount_hex, 'big')
                    else:
                        amount = int(amount_hex, 16)
                    
                    token_info = get_token_info(token_address)
                    
                    # Конвертируем amount в правильный формат с учетом decimals
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
                        # Если не удалось получить decimals, оставляем как есть
                        pass
                    
                    transfers.append({
                        'token': token_info,
                        'from': from_addr,
                        'to': to_addr,
                        'amount': amount
                    })
                except Exception as e:
                    print(f"Ошибка при обработке лога: {e}")
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
            'transfers': transfers
        }
    except Exception as e:
        print(f"Ошибка при анализе транзакции: {e}")
        return None

def print_transaction_info(tx_info):
    """Вывод информации о транзакции"""
    print(f"""
═══════════════════════════════════════════════
Новая транзакция:
═══════════════════════════════════════════════
Время: {datetime.fromtimestamp(tx_info['timestamp'])}
Хэш: {tx_info['hash']}
Блок: {tx_info['block_number']}
Статус: {tx_info['status']}

Отправитель: {tx_info['from']}
Получатель: {tx_info['to']}
Значение: {tx_info['value']} ETH

Газ:
----
Использовано: {tx_info['gas_used']}
Цена газа: {tx_info['gas_price']} Gwei
Общая стоимость: {tx_info['gas_cost_eth']} ETH
    """)

    if tx_info['transfers']:
        print("Информация о токенах:")
        print("══════════════════════")
        
        for transfer in tx_info['transfers']:
            token = transfer['token']
            amount = transfer['amount']
            price = token['price']
            
            # Расчет общей стоимости токенов
            total_value = amount * price if price is not None else None
            total_value_str = f"${total_value:.2f}" if total_value is not None else "Нет данных"
            
            print(f"""
Токен: {token['symbol']} ({token['address']})
└── Цена: ${token['price'] if token['price'] else 'Нет данных'}
└── От: {transfer['from']}
└── Кому: {transfer['to']}
└── Количество: {amount}
└── Общая стоимость: {total_value_str}
            """)

def monitor_transactions():
    """Мониторинг транзакций"""
    last_block = web3.eth.block_number
    print(f"Начинаем мониторинг с блока {last_block}")
    
    while True:
        try:
            current_block = web3.eth.block_number
            if current_block > last_block:
                for block_num in range(last_block + 1, current_block + 1):
                    block = web3.eth.get_block(block_num, full_transactions=True)
                    print(f"Проверяем блок {block_num}")
                    
                    for tx in block.transactions:
                        if tx['from'].lower() == WALLET_ADDRESS.lower() or \
                           (tx['to'] and tx['to'].lower() == WALLET_ADDRESS.lower()):
                            tx_receipt = web3.eth.get_transaction_receipt(tx['hash'].hex())
                            tx_info = analyze_transaction(tx, tx_receipt)
                            if tx_info:
                                print_transaction_info(tx_info)
                
                last_block = current_block
                
        except Exception as e:
            print(f"Ошибка при мониторинге: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    print("Начинаем отслеживание транзакций...")
    print(f"Отслеживаемый адрес: {WALLET_ADDRESS}")
    monitor_transactions() 