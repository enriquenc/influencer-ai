from aiogram.fsm.state import State, StatesGroup

class AddChannel(StatesGroup):
    waiting_for_channel = State()

class AddWallet(StatesGroup):
    waiting_for_wallet = State()

class WalletList(StatesGroup):
    waiting_for_wallet_list = State()