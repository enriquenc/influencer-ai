import json
from pathlib import Path
from typing import TypedDict, Optional
from dataclasses import dataclass

class OpenAIConfig(TypedDict):
    api_key: str
    model: str  # e.g., "gpt-3.5-turbo"
    temperature: float  # e.g., 0.7

class Config(TypedDict):
    openai: OpenAIConfig
    max_posts_per_batch: int  # e.g., 10
    debug_mode: bool

DEFAULT_CONFIG: Config = {
    "openai": {
        "api_key": "",  # Will be overridden by actual key
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
    },
    "max_posts_per_batch": 10,
    "debug_mode": False
}

def validate_config(config: dict) -> tuple[bool, Optional[str]]:
    """Validate the configuration format and values"""
    try:
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"

        if "openai" not in config:
            return False, "Missing 'openai' section in config"

        openai_config = config["openai"]
        if not isinstance(openai_config, dict):
            return False, "'openai' section must be a dictionary"

        required_openai_fields = {"api_key", "model", "temperature"}
        missing_fields = required_openai_fields - set(openai_config.keys())
        if missing_fields:
            return False, f"Missing required OpenAI fields: {missing_fields}"

        # Check for placeholder API keys
        placeholder_keys = ['your-openai-api-key-here', 'YOUR-API-KEY-HERE', 'your-api-key-here', 'sk-your-api-key']
        if openai_config["api_key"] in placeholder_keys:
            return False, "Please replace the placeholder API key in config.json with your actual OpenAI API key"

        if not isinstance(openai_config["temperature"], (int, float)):
            return False, "OpenAI temperature must be a number"

        if not (0 <= openai_config["temperature"] <= 1):
            return False, "OpenAI temperature must be between 0 and 1"

        if not isinstance(config.get("max_posts_per_batch", 10), int):
            return False, "max_posts_per_batch must be an integer"

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

    # Ensure openai section is fully populated
    if 'openai' in user_config:
        config['openai'] = DEFAULT_CONFIG['openai'].copy()
        config['openai'].update(user_config['openai'])

    # Validate config
    is_valid, error_message = validate_config(config)
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_message}")

    return config