import json
from pathlib import Path
from typing import TypedDict, Optional

class TelegramConfig(TypedDict):
    api_token: str
    api_id: str
    api_hash: str

class OpenAIConfig(TypedDict):
    api_key: str
    model: str
    temperature: float

class Config(TypedDict):
    telegram: TelegramConfig
    max_messages_per_parse: int  # e.g., 1000
    debug_mode: bool
    debug_channel: str
    openai: OpenAIConfig
    max_posts_per_batch: int

DEFAULT_CONFIG: Config = {
    "telegram": {
        "api_token": "",  # Will be overridden by actual token
        "api_id": "",     # Will be overridden by actual ID
        "api_hash": ""    # Will be overridden by actual hash
    },
    "max_messages_per_parse": 1000,
    "debug_mode": False,
    "debug_channel": "UkraineNow",  # Default debug channel
    "openai": {
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
    },
    "max_posts_per_batch": 10
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

        if not isinstance(config.get("debug_channel", "UkraineNow"), str):
            return False, "debug_channel must be a string"

        openai_config = config.get("openai", {})
        if not isinstance(openai_config, dict):
            return False, "openai must be a dictionary"

        required_openai_fields = {"api_key", "model", "temperature"}
        missing_fields = required_openai_fields - set(openai_config.keys())
        if missing_fields:
            return False, f"Missing required OpenAI fields: {missing_fields}"

        # Check for empty credentials in OpenAI
        for field in required_openai_fields:
            if not openai_config.get(field):
                return False, f"OpenAI {field} cannot be empty"

        if not isinstance(config.get("max_posts_per_batch", 10), int):
            return False, "max_posts_per_batch must be an integer"

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