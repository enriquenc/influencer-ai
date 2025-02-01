import json
from pathlib import Path
from typing import TypedDict, Optional

class TelegramConfig(TypedDict):
    api_token: str
    api_id: str
    api_hash: str

class Config(TypedDict):
    telegram: TelegramConfig
    max_messages_per_parse: int  # e.g., 1000
    debug_mode: bool

DEFAULT_CONFIG: Config = {
    "telegram": {
        "api_token": "",  # Will be overridden by actual token
        "api_id": "",     # Will be overridden by actual ID
        "api_hash": ""    # Will be overridden by actual hash
    },
    "max_messages_per_parse": 1000,
    "debug_mode": False
}

def validate_config(config: dict) -> tuple[bool, Optional[str]]:
    """Validate the configuration format and values"""
    try:
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"

        if "telegram" not in config:
            return False, "Missing 'telegram' section in config"

        telegram_config = config["telegram"]
        if not isinstance(telegram_config, dict):
            return False, "'telegram' section must be a dictionary"

        required_telegram_fields = {"api_token", "api_id", "api_hash"}
        missing_fields = required_telegram_fields - set(telegram_config.keys())
        if missing_fields:
            return False, f"Missing required Telegram fields: {missing_fields}"

        # Check for empty credentials
        for field in required_telegram_fields:
            if not telegram_config[field]:
                return False, f"Telegram {field} cannot be empty"

        if not isinstance(config.get("max_messages_per_parse", 1000), int):
            return False, "max_messages_per_parse must be an integer"

        if not isinstance(config.get("debug_mode", False), bool):
            return False, "debug_mode must be a boolean"

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"

def load_config() -> Config:
    """Load configuration from config.json in root directory"""
    config_path = Path(__file__).parent.parent / 'config.json'

    if not config_path.exists():
        raise FileNotFoundError("config.json not found in root directory")

    with open(config_path, 'r') as f:
        user_config = json.load(f)

    # Merge with defaults
    config = DEFAULT_CONFIG.copy()
    config.update(user_config)

    # Ensure telegram section is fully populated
    if 'telegram' in user_config:
        config['telegram'] = DEFAULT_CONFIG['telegram'].copy()
        config['telegram'].update(user_config['telegram'])

    # Validate config
    is_valid, error_message = validate_config(config)
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_message}")

    return config